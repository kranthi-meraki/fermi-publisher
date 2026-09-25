# Fermi publisher

Posts reels/shorts to Instagram (@fermi.ai) and YouTube (@fermi_ai) on a
schedule, from GitHub Actions. No laptop, browser or terminal needs to be open.

## How it works

```
queue/queue.jsonl     one record per video: slot time, caption, YT title/desc/tags
state/state.json      per-video status, committed back after every run
.github/workflows     runs the worker every 15 min (UTC cron; the queue decides)
```

The worker asks "what is due?" rather than firing one cron per slot. GitHub's
scheduled runners are routinely 5-20 minutes late and sometimes skip a run
entirely, so a slot-per-cron design silently drops posts. A late run catches up;
a slot more than `GRACE_MINUTES` (90) late is marked SKIPPED rather than posted
at the wrong time of day.

Videos are served to Meta and YouTube as **GitHub release assets** on
`kranthi-meraki/fermi-reel-assets` (tag `reels-auto`). Meta cannot take a local
file and needs a fetchable URL; releases do that for free, so there is no S3/R2
bill and no extra credential.

## Setup (one time)

1. **Secret** `COMPOSIO_API_KEY` - Composio dashboard -> API key.
   The key in `~/.composio/user_data.json` on the laptop is **invalid (401)**;
   this session's access came from the MCP server's own OAuth, which a headless
   worker cannot reuse. Nothing publishes until a valid key is set.
   `gh secret set COMPOSIO_API_KEY -R <owner>/fermi-publisher`
2. **Secret** `ASSET_REPO_TOKEN` - only if the asset repo is in a different
   account from this one. Otherwise the default `github.token` is enough.
3. Enable Actions on the repo (Settings -> Actions -> Allow all).

## Routine (on the laptop, every week or two)

```bash
python3 tools/make_batch.py -n 45 --start 2026-09-23   # draft captions + slots
#   ... review queue/queue.jsonl, fix anything marked DRAFT-CHECK-PRINCIPLE ...
python3 tools/stage_assets.py                          # upload those MP4s to the release
git add queue state && git commit -m "batch" && git push
```

Then it runs itself.

## Schedule

7 slots a day, 12:10-17:40 IST, irregular gaps (`publisher/schedule.py`).
904 remaining videos = about 130 days.

Cut from 48/day on 25 Sep after measuring 116 reels over the first 2.4 days:

| Block (IST) | n | Median views | Breakout rate |
|---|---|---|---|
| 12-17 | 16 | 198 | 25% |
| 06-11 | 24 | 158 | 8% |
| 18-23 | 38 | 137 | 8% |
| 00-05 | 38 | 137 | 5% |

The afternoon edge is suggestive, not proven (n=16, p is about 0.09). The
firmer reason to cut volume: 9% of reels earned 41% of all views, and the
other 91% reached a median of 126 accounts - fewer than the account has
followers. Volume was manufacturing invisible posts, not reach.

Also measured, and worth not re-learning:
- Static image cards: median 22 views vs 148 for reels. This is a reels account.
- Pacing 20s vs 8min apart made no difference to views (124 vs 127). Spacing
  avoids the action block; it does not buy reach.
- Machine-drafted captions slightly beat hand-written ones (150 vs 138), so the
  hook-and-hashtag rewrite was not the lever it was assumed to be.
- 8 comments across 116 reels. Reply-prompts do not work; shares run 12x higher.

Two things this cadence runs into:

- **YouTube caps uploads per channel per day.** This channel was cut off at 29
  with "user has exceeded the number of videos they may upload". `YT_DAILY_CAP`
  (default 25) stops the worker uploading past it; Instagram keeps going, and
  the skipped videos stay PENDING for YouTube rather than burning attempts.
- **GitHub's scheduler is not punctual.** Measured on this repo: a `*/15` cron
  fired roughly once every 90 minutes. The cron now asks every 5 minutes (the
  shortest GitHub accepts) and `MAX_PER_RUN=5` with `GRACE_MINUTES=240` lets a
  sparse run clear its backlog instead of silently skipping slots.
- **The repo is public on purpose.** Private repos get 2,000 free Actions
  minutes a month; this schedule needs 4,300-7,200, so a private repo would stop
  posting within a fortnight, quota-exhausted. Public repos get unlimited free
  minutes. No secret is in the tree - the Composio key lives in Actions secrets.
- **Scheduled workflows are disabled after 60 days of repository inactivity.**
  Not a risk here: the worker commits `state/state.json` on every run, which
  counts as activity and keeps the schedule alive indefinitely.

## Guards, and why each exists

| Guard | Because |
|---|---|
| Read the caption back after publishing | 19 of 50 reels on 18 Sep published with `caption: null`, and the Graph API cannot add one afterwards |
| Check recent media before any publish retry | A publish that times out in the MCP/API layer may already have succeeded |
| Honour a 409 "already published" as success | Instagram refuses a second publish per container; that is the real duplicate guard |
| Compare YouTube titles before upload | YouTube has no idempotency key and will happily upload twice |
| `concurrency` group on the workflow | Two overlapping runs must never publish the same item |
| Container `ERROR` -> new container, never reuse | An errored container can never be published |
| Exponential backoff, max 4 attempts | Each refused publish is itself an action that feeds an action block |

## Ceilings, measured on these accounts

- YouTube cut us off at **29 uploads in one day** (per-channel limit, not API quota).
- Instagram documents 100 posts/24h. Not the binding constraint; **pacing is**.
- 15/day on both is comfortable. 15/hour is not.
