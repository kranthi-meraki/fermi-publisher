# -*- coding: utf-8 -*-
"""Build a queue batch: pick unposted videos, draft captions from their
narration scripts, assign schedule slots, emit queue.jsonl.

Run on the laptop (it needs build/v2/*.json and the MP4s). The cloud worker
then needs nothing but the queue and the staged release assets.

Captions here are DRAFTS for review. The generator's job is to get the
structure right - hook on line 1, the myth-kill, the named principle, a
reply-prompt, and a hashtag set that differs from its neighbours - not to
be the final word.
"""
import argparse, json, os, re, random, sys
from datetime import date, datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from publisher.schedule import plan, SLOTS
from tools.captiongen import draft, clean

VIDEOS = "/Users/Kranthi/Desktop/Projects/videos"
V2 = f"{VIDEOS}/build/v2"
IMPROVED = f"{VIDEOS}/build/out/v2_improved"



def load_script(slug):
    p = os.path.join(V2, f"{slug}.json")
    if not os.path.exists(p):
        return None
    return json.load(open(p))






def yt_title(hook, slug):
    t = clean(hook).rstrip("?.!")
    t = re.sub(r"^(so|and|but)\s+", "", t, flags=re.I)
    if len(t) > 95:
        t = t[:92].rsplit(" ", 1)[0]
    if clean(hook).endswith("?"):
        t += "?"
    return t[0].upper() + t[1:]


def posted_slugs():
    done = set()
    cj = os.path.join(IMPROVED, "captions.json")
    if os.path.exists(cj):
        done |= set(json.load(open(cj))["order"])
    st = os.path.join(IMPROVED, "batch3", "state.json")
    if os.path.exists(st):
        s = json.load(open(st))
        done |= set(s.get("published", {}))
        done |= set(s.get("remaining_unposted", []))   # already captioned by hand
    return done


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-n", "--count", type=int, default=45)
    ap.add_argument("--start", default=None, help="YYYY-MM-DD, default tomorrow")
    ap.add_argument("--out", default=None)
    ap.add_argument("--seed", type=int, default=7)
    a = ap.parse_args()

    random.seed(a.seed)
    done = posted_slugs()
    pool = []
    for f in sorted(os.listdir(IMPROVED)):
        if not (f.startswith("v2-") and f.endswith(".mp4")):
            continue
        slug = f[3:-4]
        if slug in done:
            continue
        d = load_script(slug)
        if not d or not d.get("cues"):
            continue
        pool.append((slug, f, d))
    def accessibility(rec):
        slug = rec[0]
        m = re.match(r"s(\d+)", slug)
        series = int(m.group(1)) if m else -1      # plain names first
        return (series, slug)
    # take the most accessible tier, then shuffle inside it so a single day
    # is not three variations on one theme
    random.shuffle(pool)
    pool.sort(key=accessibility)
    pool = pool[:a.count * 3]
    random.shuffle(pool)
    pool = pool[:a.count]

    start = (datetime.strptime(a.start, "%Y-%m-%d").date() if a.start
             else date.fromordinal(date.today().toordinal() + 1))
    times = plan(start, len(pool))

    out = a.out or os.path.join(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))), "queue", "queue.jsonl")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w") as fh:
        for i, ((slug, fname, d), when) in enumerate(zip(pool, times)):
            cap, tags, confident = draft(d['cues'], i)
            hook = clean(d["cues"][0]["vo"])
            rec = {
                "id": slug,
                "file": fname,
                "scheduled_at": when,
                "caption": cap,
                "yt_title": yt_title(hook, slug),
                "yt_description": re.sub(r"\n\n#.*$", "", cap, flags=re.S)
                                   + "\n\nfermi.ai\n\n#Shorts #physics",
                "yt_tags": [t.lstrip("#") for t in tags[:10]],
                "review": "DRAFT" if confident else "DRAFT-CHECK-PRINCIPLE",
            }
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print(f"wrote {len(pool)} items to {out}")
    print(f"first slot {times[0]}  last slot {times[-1]}")
    print(f"excluded {len(done)} already-posted slugs")


if __name__ == "__main__":
    main()
