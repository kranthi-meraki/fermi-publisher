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
HALF_HOURLY = ['00:05', '00:37', '01:03', '01:33', '02:03', '02:37', '03:05', '03:39', '04:07', '04:41', '05:15', '05:49', '06:15', '06:41', '07:07', '07:35', '08:01', '08:27', '08:57', '09:29', '10:03', '10:35', '11:05', '11:33', '11:59', '12:25', '12:53', '13:25', '13:53', '14:21', '14:49', '15:17', '15:49', '16:15', '16:41', '17:07', '17:39', '18:05', '18:33', '19:03', '19:29', '20:01', '20:33', '21:01', '21:29', '21:59', '22:27', '22:53', '23:27', '23:59']


# One post every ~2 hours, jittered. 12/day. Chosen over 48/day after this
# account tripped Instagram's code 9 action block twice on 1 Oct, and after
# the @fermi.ai measurement that 48/day left 91% of posts reaching fewer
# accounts than the account had followers.
TWO_HOURLY = ['00:12', '02:00', '04:05', '05:53', '07:48', '09:40', '11:52', '13:52', '15:47', '17:52', '19:40', '21:45', '23:45']
