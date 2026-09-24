"""Publishing worker. Runs every ~15 min, asks what is due, posts it.

Runs late-tolerant on purpose: GitHub's scheduled runners routinely fire
5-20 minutes behind and sometimes skip a run entirely, so the queue - not
cron - decides what goes out. A missed run is caught by the next one.
"""
import argparse, json, os, subprocess, sys, time, traceback
from datetime import timedelta
from .composio_client import Composio, ComposioError
from . import assets, instagram, youtube
from .schedule import now_ist, IST

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
QUEUE = os.path.join(ROOT, "queue", "queue.jsonl")
STATE = os.path.join(ROOT, "state", "state.json")

MAX_PER_RUN = int(os.environ.get("MAX_PER_RUN", "5"))
MAX_ATTEMPTS = 4
# YouTube enforces a per-channel daily upload limit. This channel was cut off
# at 29 in one day with "user has exceeded the number of videos they may
# upload". At 48 posts/day that ceiling is reached every afternoon, so the
# worker stops uploading rather than burning attempts on guaranteed failures;
# Instagram continues unaffected.
YT_DAILY_CAP = int(os.environ.get("YT_DAILY_CAP", "25"))
GRACE_MINUTES = int(os.environ.get("GRACE_MINUTES", "240"))
# Measured on this repo: a */15 cron actually fired once in 70 minutes.
# GitHub throttles frequent schedules, so the grace window has to be wide
# enough that a sparse run still catches its slots, and a single run has
# to be allowed to clear a small backlog.


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


def yt_today(st=None):
    """How many YouTube uploads already succeeded today (IST)."""
    st = st if st is not None else load_state()
    today = now_ist().date().isoformat()
    return sum(1 for v in st.values()
               if v.get("youtube", {}).get("status") == "DONE"
               and (v["youtube"].get("at") or "").startswith(today))


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
        # a queue record may pin itself to one platform (e.g. Instagram only)
        allowed = it.get("platforms") or platforms
        wants = [p for p in platforms if p in allowed
                 and e[p]["status"] not in ("DONE", "SKIPPED")]
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
            # a recently staged asset can take minutes to become fetchable on
            # GitHub's CDN; be patient before declaring it missing, and let the
            # backoff retry rather than burning an attempt
            if not assets.url_ok(url, tries=5, delay=20):
                raise RuntimeError(f"asset not fetchable yet: {url}")

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

            if "youtube" in wants and yt_today(st) >= YT_DAILY_CAP:
                log(f"youtube daily cap reached ({YT_DAILY_CAP}); deferring")
                e["attempts"] -= 1          # not this item's fault
                wants = [w for w in wants if w != "youtube"]

            if "youtube" in wants:
                seen = youtube.recent_titles(cx)
                if it["yt_title"].strip() in seen:
                    e["youtube"] = {"status": "DONE",
                                    "video_id": seen[it["yt_title"].strip()],
                                    "note": "already on channel", "at": now_ist().isoformat()}
                    log("youtube: title already on channel, skipping upload")
                else:
                    yid = youtube.upload_from_url(
                        cx, url, it["file"], it["yt_title"],
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


def commit_state():
    """Push state back mid-loop so a killed runner loses no record."""
    for cmd in (["git", "add", "state/state.json"],
                ["git", "-c", "user.name=fermi-publisher",
                 "-c", "user.email=bot@users.noreply.github.com",
                 "commit", "-m", f"state: {now_ist().isoformat()}"],
                ["git", "pull", "--rebase", "--autostash", "-q",
                 "-X", "ours", "origin", "master"],
                ["git", "push", "-q", "origin", "HEAD:master"]):
        subprocess.run(cmd, cwd=ROOT, capture_output=True)


def loop(minutes, platforms, tick=60):
    """Stay resident and do our own timing.

    GitHub's scheduler is the weak link: measured on this repo, a */5 cron
    delivered ZERO runs in 27 minutes and a */15 cron about one run per 90
    minutes. Rather than depend on it firing punctually, one run stays alive
    for hours. The workflow's concurrency group keeps exactly one successor
    queued, so the moment this run ends the next begins - coverage is
    continuous as long as the cron lands occasionally.
    """
    deadline = now_ist() + timedelta(minutes=minutes)
    log(f"loop mode: working until {deadline.strftime('%H:%M')} IST")
    posted = 0
    while now_ist() < deadline:
        n_before = sum(1 for v in load_state().values()
                       if v.get("instagram", {}).get("status") == "DONE")
        try:
            run(False, platforms)
        except Exception:
            traceback.print_exc()
        n_after = sum(1 for v in load_state().values()
                      if v.get("instagram", {}).get("status") == "DONE")
        if n_after != n_before:
            posted += n_after - n_before
            commit_state()
        time.sleep(tick)
    log(f"loop finished; {posted} posted this run")
    commit_state()
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--platforms", default="instagram,youtube")
    ap.add_argument("--loop-minutes", type=int, default=0,
                    help="stay resident this many minutes, posting on time")
    a = ap.parse_args()
    plats = tuple(p.strip() for p in a.platforms.split(","))
    if a.loop_minutes and not a.dry_run:
        sys.exit(loop(a.loop_minutes, plats))
    sys.exit(run(a.dry_run, plats))


if __name__ == "__main__":
    main()
