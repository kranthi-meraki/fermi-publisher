"""Slot planning.

7 posts a day inside the 12:00-18:00 IST window.
"""
from datetime import datetime, timedelta, timezone

IST = timezone(timedelta(hours=5, minutes=30))

# 7 posts a day, 12:00-18:00 IST only, irregular gaps.
#
# Measured over 116 reels (22-25 Sep): the 12-17 block returned a median 198
# views and a 25% breakout rate, against 137/5-8% for night and evening. The
# sample is small (n=16) so this is a bias, not a certainty. The stronger
# reason to cut from 48/day is that 91% of posts reached a median of 126
# accounts - below the follower count - so volume was producing near-invisible
# posts rather than reach. Irregular gaps because burst pacing, not daily
# volume, is what triggers Instagram's action block.
SLOTS = ["12:10", "13:05", "14:00", "15:00", "15:55", "16:50", "17:40"]


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
