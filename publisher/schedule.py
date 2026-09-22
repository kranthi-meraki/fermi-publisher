"""Slot planning.

48 posts a day, every 30 minutes, round the clock (IST).
"""
from datetime import datetime, timedelta, timezone

IST = timezone(timedelta(hours=5, minutes=30))

# every 30 minutes, round the clock: 48 posts a day
SLOTS = [f"{h:02d}:{m:02d}" for h in range(24) for m in (0, 30)]


def plan(start, n_items, slots=None, after=None):
    """ISO timestamps for n_items over consecutive days.

    `start` is a date. `after` (a datetime) drops any slot at or before it, so
    a mid-day replan begins at the next free slot rather than back-dating
    everything to midnight.
    """
    slots = slots or SLOTS
    out, day = [], start
    while len(out) < n_items:
        for hhmm in slots:
            if len(out) >= n_items:
                break
            h, m = map(int, hhmm.split(":"))
            t = datetime(day.year, day.month, day.day, h, m, tzinfo=IST)
            if after and t <= after:
                continue
            out.append(t.isoformat())
        day += timedelta(days=1)
    return out


def now_ist():
    return datetime.now(IST)
