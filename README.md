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

15 slots a day, irregular gaps, 07:10-22:50 IST (`publisher/schedule.py`).
Irregular matters: the Instagram action block on 18 Sep came from burst pacing
(53 posts in 8 minutes), not from daily volume, and the quota endpoint showed
headroom the whole time. Evenly spaced posting also reads as automated.

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
