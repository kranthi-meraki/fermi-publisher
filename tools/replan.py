#!/usr/bin/env python3
"""Re-assign slot times in place. Captions, ids, files and release tranches
are untouched, so nothing drifts out of step with the uploaded assets."""
import json, os, sys
from datetime import date, datetime
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from publisher.schedule import plan

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
Q = os.path.join(ROOT, "queue", "queue.jsonl")
from publisher.schedule import now_ist
if len(sys.argv) > 1 and sys.argv[1] != "now":
    start, after = datetime.strptime(sys.argv[1], "%Y-%m-%d").date(), None
else:
    n = now_ist()
    start, after = n.date(), n            # begin at the next free slot
rows = [json.loads(l) for l in open(Q) if l.strip()]
for r, when in zip(rows, plan(start, len(rows), after=after)):
    r["scheduled_at"] = when
with open(Q, "w") as fh:
    for r in rows:
        fh.write(json.dumps(r, ensure_ascii=False) + "\n")
print(f"replanned {len(rows)} items")
print("first:", rows[0]["scheduled_at"], " last:", rows[-1]["scheduled_at"])
print("days:", len({r['scheduled_at'][:10] for r in rows}))
