"""Slot planning.

48 posts a day, every 30 minutes, round the clock (IST).
"""
from datetime import datetime, timedelta, timezone

IST = timezone(timedelta(hours=5, minutes=30))

# every 30 minutes, round the clock: 48 posts a day
SLOTS = [f"{h:02d}:{m:02d}" for h in range(24) for m in (0, 30)]


def plan(start_date, n_items, slots=None):
    """Yield ISO timestamps for n_items spread over consecutive days."""
    slots = slots or SLOTS
    out, day = [], start_date
    while len(out) < n_items:
        for hhmm in slots:
            if len(out) >= n_items:
                break
            h, m = map(int, hhmm.split(":"))
            out.append(datetime(day.year, day.month, day.day, h, m, tzinfo=IST).isoformat())
        day += timedelta(days=1)
    return out


def now_ist():
    return datetime.now(IST)
