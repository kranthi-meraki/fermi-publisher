"""Instagram Reels publishing, with the guards this account has already needed."""
import time
from .composio_client import Composio, ComposioError

IG_USER_ID = "29611910468397943"          # @fermi.ai
ACCOUNT = "instagram_johnin-creole"


def create_container(cx: Composio, video_url, caption):
    d = cx.execute("INSTAGRAM_POST_IG_USER_MEDIA", {
        "ig_user_id": IG_USER_ID, "media_type": "REELS", "share_to_feed": True,
        "video_url": video_url, "caption": caption}, ACCOUNT)
    cid = d.get("id")
    if not cid:
        raise ComposioError(f"no container id: {str(d)[:200]}")
    return cid


def container_status(cx: Composio, creation_id):
    d = cx.execute("INSTAGRAM_GET_POST_STATUS", {"creation_id": creation_id}, ACCOUNT)
    return d.get("status") or d.get("status_code")


def already_published(cx: Composio, caption_head, since_minutes=30):
    """Is a post whose caption starts with this text already live?
    Used INSTEAD of blind-retrying a publish that timed out."""
    d = cx.execute("INSTAGRAM_GET_IG_USER_MEDIA", {
        "ig_user_id": "me", "limit": 10,
        "fields": "id,caption,shortcode,timestamp"}, ACCOUNT)
    head = " ".join(caption_head.split())[:40]
    for m in (d.get("data") or []):
        cap = m.get("caption") or ""
        if head and " ".join(cap.split()).startswith(head):
            return m
    return None


def publish(cx: Composio, creation_id, max_wait=240):
    d = cx.execute("INSTAGRAM_POST_IG_USER_MEDIA_PUBLISH", {
        "ig_user_id": IG_USER_ID, "creation_id": creation_id,
        "max_wait_seconds": max_wait}, ACCOUNT)
    return d.get("id")


def verify_caption(cx: Composio, media_id):
    """19 of the 50 reels on 18 Sep published with caption: null and the
    Graph API cannot fix that after the fact. Always read it back."""
    d = cx.execute("INSTAGRAM_GET_IG_MEDIA", {
        "ig_media_id": media_id,
        "fields": "id,shortcode,permalink,timestamp,caption"}, ACCOUNT)
    return d


def post_reel(cx: Composio, video_url, caption, log):
    """Returns (media_id, shortcode, permalink, caption_ok)."""
    existing = already_published(cx, caption)
    if existing:
        log(f"already live as {existing.get('shortcode')} - not reposting")
        mid = existing["id"]
    else:
        cid = create_container(cx, video_url, caption)
        log(f"container {cid}")
        for _ in range(40):
            st = container_status(cx, cid)
            if st == "FINISHED":
                break
            if st == "ERROR":
                raise ComposioError("container ERROR - recreate with a fresh container")
            time.sleep(6)
        else:
            raise ComposioError("container never reached FINISHED")
        try:
            mid = publish(cx, cid)
        except ComposioError as e:
            if "already been PUBLISHED" in str(e) or "409" in str(e):
                found = already_published(cx, caption)
                if not found:
                    raise
                mid = found["id"]
                log("publish reported 409; post is live")
            else:
                raise
    meta = verify_caption(cx, mid)
    cap_ok = bool(meta.get("caption"))
    return mid, meta.get("shortcode"), meta.get("permalink"), cap_ok
