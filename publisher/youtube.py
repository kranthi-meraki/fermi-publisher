"""YouTube Shorts upload.

YOUTUBE_MULTIPART_UPLOAD_VIDEO needs {name, mimetype, s3key}, and an s3key can
only come from a prior Composio action - a chicken-and-egg for a file that
lives on a public URL. The workbench solves it: pull the URL into the mounted
filesystem there, mint a key from it, upload. Channel upload cap is per channel
per day; this account was cut off at 29 in one day.
"""
import json
from .composio_client import Composio, ComposioError

ACCOUNT = "youtube_stere-bahima"
CATEGORY_EDUCATION = "27"

_UPLOAD = '''
import json, os, subprocess
os.makedirs("/mnt/files/pub", exist_ok=True)
path = "/mnt/files/pub/" + {fname!r}
if not (os.path.exists(path) and os.path.getsize(path) > 1000000):
    tmp = "/tmp/" + {fname!r}
    subprocess.run(["curl","-sL","--retry","3","-o",tmp,{url!r}], check=False)
    # the s3fs mount rejects large single writes; chunk it
    with open(tmp,"rb") as fi, open(path,"wb") as fo:
        while True:
            b = fi.read(1048576)
            if not b: break
            fo.write(b); fo.flush(); os.fsync(fo.fileno())
key = get_mount_file_s3_key(path)[0]
# the mount is small and shared; leaving each MP4 behind filled it and every
# later upload died with [Errno 28] No space left on device
import glob
for old in glob.glob("/mnt/files/pub/*.mp4"):
    if old != path:
        try: os.remove(old)
        except OSError: pass
res, err = run_composio_tool("YOUTUBE_MULTIPART_UPLOAD_VIDEO", {{
    "title": {title!r}, "description": {desc!r}, "tags": {tags!r},
    "categoryId": "27", "privacyStatus": {privacy!r},
    "videoFile": {{"name": {fname!r}, "mimetype": "video/mp4", "s3key": key}}}},
    account="youtube_stere-bahima")
try: os.remove(path)
except OSError: pass
try: os.remove("/tmp/" + {fname!r})
except OSError: pass
print("RESULT " + json.dumps({{"err": str(err)[:300] if err else None,
      "id": ((res or {{}}).get("data") or {{}}).get("video", {{}}).get("id")}}))
'''


def upload_from_url(cx: Composio, url, fname, title, description, tags,
                    privacy="public"):
    code = _UPLOAD.format(fname=fname, url=url, title=title[:100],
                          desc=description, tags=tags, privacy=privacy)
    out = cx.workbench(code, thought="upload a short to YouTube", step="YT_UPLOAD")
    line = next((l for l in out.splitlines() if l.startswith("RESULT ")), None)
    if not line:
        raise ComposioError(f"no RESULT from workbench: {out[-400:]}")
    d = json.loads(line[7:])
    if d.get("err") or not d.get("id"):
        raise ComposioError(f"youtube upload failed: {d.get('err')}")
    return d["id"]


def recent_titles(cx: Composio, limit=25):
    """No idempotency key exists on videos.insert, so compare titles first.

    NOT race-proof: the uploads listing lags a fresh upload by seconds, so two
    workers starting inside that window both see "not present" and both upload.
    This happened once - a local run and a cloud run three seconds apart made
    two copies of one short. The real guard is never running a second worker
    against this account while the workflow is live.
    """
    d = cx.execute("YOUTUBE_LIST_CHANNEL_VIDEOS",
                   {"mine": True, "maxResults": limit, "part": "snippet"},
                   ACCOUNT, thought="check for a duplicate upload", step="YT_DEDUPE")
    out = {}
    for i in (d.get("items") or []):
        sn = i.get("snippet") or {}
        vid = (sn.get("resourceId") or {}).get("videoId")
        if sn.get("title"):
            out[sn["title"].strip()] = vid
    return out
