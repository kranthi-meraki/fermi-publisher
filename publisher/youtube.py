"""YouTube Shorts upload. Channel cap is per-channel per-day; we hit it at 29."""
from .composio_client import Composio, ComposioError

ACCOUNT = "youtube_stere-bahima"
CATEGORY_EDUCATION = "27"


def upload(cx: Composio, local_path, title, description, tags, privacy="public"):
    video_file = cx.upload_file(local_path, "youtube", "YOUTUBE_MULTIPART_UPLOAD_VIDEO")
    d = cx.execute("YOUTUBE_MULTIPART_UPLOAD_VIDEO", {
        "title": title[:100], "description": description, "tags": tags,
        "categoryId": CATEGORY_EDUCATION, "privacyStatus": privacy,
        "videoFile": video_file}, ACCOUNT)
    vid = ((d.get("video") or {}) or {}).get("id") or d.get("id")
    if not vid:
        raise ComposioError(f"no video id: {str(d)[:200]}")
    return vid


def recent_titles(cx: Composio, limit=20):
    """Guard against double-upload: YouTube has no idempotency key, so we
    check the channel's recent titles before uploading."""
    d = cx.execute("YOUTUBE_LIST_CHANNEL_VIDEOS", {
        "mine": True, "maxResults": limit, "part": "snippet"}, ACCOUNT)
    out = {}
    for i in (d.get("items") or []):
        sn = i.get("snippet") or {}
        vid = (sn.get("resourceId") or {}).get("videoId")
        if sn.get("title"):
            out[sn["title"].strip()] = vid
    return out
