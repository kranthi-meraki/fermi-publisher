#!/usr/bin/env python3
"""Upload every MP4 referenced by the queue to the asset release, so the
cloud worker needs nothing from this laptop."""
import json, os, subprocess, sys, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from publisher import assets

SRC = "/Users/Kranthi/Desktop/Projects/videos/build/out/v2_improved"
Q = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                 "queue", "queue.jsonl")

rows = [json.loads(l) for l in open(Q) if l.strip()]
assets.ensure_release()
present = assets.existing_assets()
done = skipped = 0
failed = []
for r in rows:
    path = os.path.join(SRC, r["file"])
    if not os.path.exists(path):
        print(f"MISSING {r['file']}"); continue
    if r["file"] in present:
        skipped += 1; continue
    print(f"uploading {r['file']}", flush=True)
    for attempt in range(3):
        try:
            assets.ensure_uploaded(path, print, known=present)
            present.add(r["file"]); done += 1
            break
        except Exception as ex:
            # uploads.github.com returns a transient 400 often enough that
            # one bad file must not abort the whole batch
            print(f"  attempt {attempt+1} failed: {str(ex)[:160]}", flush=True)
            time.sleep(5 * (attempt + 1))
    else:
        failed.append(r["file"])
print(f"uploaded {done}, already present {skipped}, failed {len(failed)}, total {len(rows)}")
if failed: print("FAILED:", failed)
