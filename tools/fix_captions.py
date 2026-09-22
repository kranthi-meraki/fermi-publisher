#!/usr/bin/env python3
"""Re-draft captions in place, preserving id, slot, release tag and URL.

Editing the existing queue rather than regenerating it means the schedule and
the release tranches cannot drift out of step with assets already uploaded.
"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tools.captiongen import draft, clean
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
Q = os.path.join(ROOT, "queue", "queue.jsonl")
V2 = "/Users/Kranthi/Desktop/Projects/videos/build/v2"

rows = [json.loads(l) for l in open(Q) if l.strip()]
before_flagged = sum(1 for r in rows if r["review"] != "DRAFT")
changed = 0
for i, r in enumerate(rows):
    d = json.load(open(os.path.join(V2, f"{r['id']}.json")))
    cap, tags, named = draft(d["cues"], i)
    if cap != r["caption"]:
        changed += 1
    r["caption"] = cap
    r["yt_tags"] = [t.lstrip("#") for t in tags[:10]]
    r["yt_description"] = (re.sub(r"\n\n#.*$", "", cap, flags=re.S)
                           + "\n\nfermi.ai\n\n#Shorts #physics")
    r["review"] = "DRAFT" if named else "NEEDS-CONCEPT"

with open(Q, "w") as fh:
    for r in rows:
        fh.write(json.dumps(r, ensure_ascii=False) + "\n")

after = sum(1 for r in rows if r["review"] != "DRAFT")
print(f"rewrote {changed}/{len(rows)} captions")
print(f"flagged: {before_flagged} -> {after}")
