#!/usr/bin/env python3
"""Upload every MP4 referenced by the queue to the asset release, so the
cloud worker needs nothing from this laptop."""
import json, os, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from publisher import assets

SRC = "/Users/Kranthi/Desktop/Projects/videos/build/out/v2_improved"
Q = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                 "queue", "queue.jsonl")

rows = [json.loads(l) for l in open(Q) if l.strip()]
assets.ensure_release()
present = assets.existing_assets()
done = skipped = 0
for r in rows:
    path = os.path.join(SRC, r["file"])
    if not os.path.exists(path):
        print(f"MISSING {r['file']}"); continue
    if r["file"] in present:
        skipped += 1; continue
    print(f"uploading {r['file']}", flush=True)
    assets.ensure_uploaded(path, print, known=present)
    present.add(r["file"])
    done += 1
print(f"uploaded {done}, already present {skipped}, total {len(rows)}")
