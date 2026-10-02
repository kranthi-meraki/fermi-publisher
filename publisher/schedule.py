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

# One post an hour, around the clock. Minutes are irregular on purpose: a
# fixed :00 cadence is the pattern Instagram's action-block heuristics watch
# for, and burst pacing - not daily volume - is what triggered code 9 here.
HOURLY = [f"{h:02d}:{m:02d}" for h, m in zip(range(24), [7, 2, 14, 5, 14, 8, 14, 26, 20, 8, 20, 26, 20, 14, 20, 29, 41, 50, 44, 32, 44, 50, 57, 48])]


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


# Two posts an hour, jittered. 48/day is aggressive for this account -
# it tripped Instagram's code 9 action block twice on 1 Oct at ~30 posts/day.
HALF_HOURLY = ['00:04', '00:29', '01:01', '01:26', '01:54', '02:21', '02:56', '03:26', '03:54', '04:26', '04:51', '05:23', '05:53', '06:25', '06:53', '07:18', '07:43', '08:16', '08:46', '09:16', '09:51', '10:16', '10:49', '11:24', '11:51', '12:26', '12:58', '13:30', '13:55', '14:28', '14:55', '15:27', '16:02', '16:32', '16:59', '17:26', '17:54', '18:22', '18:55', '19:23', '19:48', '20:16', '20:43', '21:15', '21:48', '22:21', '22:46', '23:14', '23:44']
