"""Slot planning.

15 posts a day at irregular gaps. Irregular matters: the action block on
18 Sep came from burst pacing, not daily volume, and evenly spaced posting
also reads as automated. Times are IST and weighted towards the evening.
"""
from datetime import datetime, timedelta, timezone

IST = timezone(timedelta(hours=5, minutes=30))

SLOTS = ["07:10", "08:25", "09:40", "11:05", "12:20",
         "13:35", "14:55", "16:10", "17:25", "18:40",
         "19:50", "20:35", "21:20", "22:05", "22:50"]


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
