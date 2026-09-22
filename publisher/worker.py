"""Publishing worker. Runs every ~15 min, asks what is due, posts it.

Runs late-tolerant on purpose: GitHub's scheduled runners routinely fire
5-20 minutes behind and sometimes skip a run entirely, so the queue - not
cron - decides what goes out. A missed run is caught by the next one.
"""
import argparse, json, os, sys, tempfile, traceback
from datetime import timedelta
import requests

from .composio_client import Composio, ComposioError
from . import assets, instagram, youtube
from .schedule import now_ist, IST

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
QUEUE = os.path.join(ROOT, "queue", "queue.jsonl")
STATE = os.path.join(ROOT, "state", "state.json")

MAX_PER_RUN = int(os.environ.get("MAX_PER_RUN", "2"))
MAX_ATTEMPTS = 4
GRACE_MINUTES = 90          # don't post a slot more than this late; skip it


def log(msg):
    print(f"[{now_ist().strftime('%Y-%m-%d %H:%M:%S')}] {msg}", flush=True)


def load_queue():
    items = []
    with open(QUEUE) as fh:
        for line in fh:
            line = line.strip()
            if line:
                items.append(json.loads(line))
    return items


def load_state():
    if not os.path.exists(STATE):
        return {}
    with open(STATE) as fh:
        return json.load(fh)


def save_state(st):
    os.makedirs(os.path.dirname(STATE), exist_ok=True)
    with open(STATE, "w") as fh:
        json.dump(st, fh, indent=1, sort_keys=True)


def entry(st, vid):
    return st.setdefault(vid, {
        "instagram": {"status": "PENDING"},
        "youtube": {"status": "PENDING"},
        "attempts": 0, "last_error": None})


def backoff_ready(e, now):
    nxt = e.get("next_attempt_at")
    return not nxt or now.isoformat() >= nxt


def due_items(items, st, now, platforms):
    out = []
    for it in items:
        e = entry(st, it["id"])
        wants = [p for p in platforms if e[p]["status"] not in ("DONE", "SKIPPED")]
        if not wants:
            continue
        if it["scheduled_at"] > now.isoformat():
            continue
        if e["attempts"] >= MAX_ATTEMPTS:
            continue
        if not backoff_ready(e, now):
            continue
        sched = now.fromisoformat(it["scheduled_at"])
        if now - sched > timedelta(minutes=GRACE_MINUTES) and e["attempts"] == 0:
            log(f"{it['id']} missed its slot by >{GRACE_MINUTES}m - marking SKIPPED")
            for p in wants:
                e[p]["status"] = "SKIPPED"
            continue
        out.append((it, e, wants))
    out.sort(key=lambda t: t[0]["scheduled_at"])
    return out[:MAX_PER_RUN]


def fetch_to_tmp(url, name):
    path = os.path.join(tempfile.gettempdir(), name)
    if os.path.exists(path) and os.path.getsize(path) > 1_000_000:
        return path
    with requests.get(url, stream=True, timeout=600) as r:
        r.raise_for_status()
        with open(path, "wb") as fh:
            for chunk in r.iter_content(1 << 20):
                fh.write(chunk)
    return path


def run(dry_run=False, platforms=("instagram", "youtube")):
    items, st = load_queue(), load_state()
    now = now_ist()
    todo = due_items(items, st, now, platforms)
    if not todo:
        log("nothing due")
        save_state(st)
        return 0

    cx = None if dry_run else Composio()
    failures = 0

    for it, e, wants in todo:
        vid = it["id"]
        log(f"--- {vid} ({it['file']}) due {it['scheduled_at']} -> {wants}")
        e["attempts"] += 1
        try:
            url = it.get("video_url") or assets.public_url(it["file"])
            if dry_run:
                log(f"DRY RUN: would post {vid} to {wants} using {url}")
                continue
            if not assets.url_ok(url):
                raise RuntimeError(f"asset not fetchable: {url} - stage it first")

            if "instagram" in wants:
                mid, shortcode, permalink, cap_ok = instagram.post_reel(
                    cx, url, it["caption"], log)
                e["instagram"] = {"status": "DONE", "media_id": mid,
                                  "shortcode": shortcode, "permalink": permalink,
                                  "caption_verified": cap_ok,
                                  "at": now_ist().isoformat()}
                log(f"instagram {permalink} caption_ok={cap_ok}")
                if not cap_ok:
                    log("WARNING: caption came back null and cannot be fixed via API")

            if "youtube" in wants:
                seen = youtube.recent_titles(cx)
                if it["yt_title"].strip() in seen:
                    e["youtube"] = {"status": "DONE",
                                    "video_id": seen[it["yt_title"].strip()],
                                    "note": "already on channel", "at": now_ist().isoformat()}
                    log("youtube: title already on channel, skipping upload")
                else:
                    local = fetch_to_tmp(url, it["file"])
                    yid = youtube.upload(cx, local, it["yt_title"],
                                         it["yt_description"], it["yt_tags"])
                    e["youtube"] = {"status": "DONE", "video_id": yid,
                                    "url": f"https://www.youtube.com/watch?v={yid}",
                                    "at": now_ist().isoformat()}
                    log(f"youtube https://www.youtube.com/watch?v={yid}")
            e["last_error"] = None
        except Exception as ex:
            failures += 1
            e["last_error"] = f"{type(ex).__name__}: {ex}"[:500]
            delay = 2 ** e["attempts"] * 5
            e["next_attempt_at"] = (now_ist() + timedelta(minutes=delay)).isoformat()
            log(f"FAILED {vid}: {e['last_error']}")
            log(f"retry after {delay}m (attempt {e['attempts']}/{MAX_ATTEMPTS})")
            traceback.print_exc()
        finally:
            save_state(st)

    save_state(st)
    return 1 if failures and failures == len(todo) else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--platforms", default="instagram,youtube")
    a = ap.parse_args()
    sys.exit(run(a.dry_run, tuple(p.strip() for p in a.platforms.split(","))))


if __name__ == "__main__":
    main()
