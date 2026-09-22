#!/usr/bin/env python3
"""Upload every MP4 in the queue to its release tranche.

Resumable: re-running skips anything already on its release, so a failed or
interrupted run costs nothing. Release membership is read from the API, never
by probing the download URL - a 404 on a URL that does not exist yet gets
cached by GitHub's CDN and then outlives the upload.
"""
import json, os, subprocess, sys, time
from collections import defaultdict

SRC = "/Users/Kranthi/Desktop/Projects/videos/build/out/v2_improved"
REPO = os.environ.get("ASSET_REPO", "kranthi-meraki/fermi-reel-assets")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
Q = os.path.join(ROOT, "queue", "queue.jsonl")


def run(args):
    return subprocess.run(args, capture_output=True, text=True)


def existing(tag):
    r = run(["gh", "api", f"repos/{REPO}/releases/tags/{tag}", "-q", ".assets[].name"])
    if r.returncode != 0:
        return None            # release does not exist yet
    return {ln.strip() for ln in r.stdout.splitlines() if ln.strip()}


def ensure_release(tag):
    if existing(tag) is None:
        run(["gh", "release", "create", tag, "-R", REPO,
             "--title", f"Fermi library {tag}",
             "--notes", "Video assets served to Meta and YouTube by the publisher."])


def main():
    rows = [json.loads(l) for l in open(Q) if l.strip()]
    by_tag = defaultdict(list)
    for r in rows:
        by_tag[r["release_tag"]].append(r)

    total_up = total_skip = 0
    failed = []
    for tag in sorted(by_tag):
        ensure_release(tag)
        present = existing(tag) or set()
        todo = [r for r in by_tag[tag] if r["file"] not in present]
        print(f"[{tag}] {len(by_tag[tag])} files, {len(todo)} to upload", flush=True)
        total_skip += len(by_tag[tag]) - len(todo)
        for r in todo:
            path = os.path.join(SRC, r["file"])
            if not os.path.exists(path):
                print(f"  MISSING {r['file']}"); failed.append(r["file"]); continue
            for attempt in range(3):
                res = run(["gh", "release", "upload", tag, "-R", REPO, path, "--clobber"])
                if res.returncode == 0:
                    total_up += 1
                    break
                # uploads.github.com throws transient 400s; one file must not
                # abort a run of a thousand
                print(f"  retry {r['file']}: {res.stderr.strip()[:120]}", flush=True)
                time.sleep(5 * (attempt + 1))
            else:
                failed.append(r["file"])
            if total_up % 25 == 0 and total_up:
                print(f"  ... {total_up} uploaded", flush=True)
    print(f"DONE uploaded={total_up} already_present={total_skip} failed={len(failed)}")
    if failed:
        print("FAILED:", failed[:20])
        json.dump(failed, open(os.path.join(ROOT, "state", "stage_failed.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
