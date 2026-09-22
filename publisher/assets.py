"""Public video URLs via GitHub release assets. Meta must be able to fetch
the URL; it cannot take a local file, and a Composio s3key needs a prior
Composio action, so releases are the cheap way to host these."""
import os, subprocess
import requests

REPO = os.environ.get("ASSET_REPO", "kranthi-meraki/fermi-reel-assets")
TAG = os.environ.get("ASSET_TAG", "reels-auto")
BASE = f"https://github.com/{REPO}/releases/download/{TAG}"


def _run(args):
    return subprocess.run(args, capture_output=True, text=True)


def ensure_release():
    r = _run(["gh", "release", "view", TAG, "-R", REPO])
    if r.returncode != 0:
        _run(["gh", "release", "create", TAG, "-R", REPO,
              "--title", f"Fermi auto-publish assets ({TAG})",
              "--notes", "Assets served to Meta/YouTube by the publisher worker."])


def public_url(filename):
    return f"{BASE}/{filename}"


def url_ok(url):
    try:
        r = requests.get(url, headers={"Range": "bytes=0-0"}, timeout=60,
                         allow_redirects=True)
        return r.status_code in (200, 206)
    except requests.RequestException:
        return False


def ensure_uploaded(local_path, log):
    """Upload the asset if the URL is not already fetchable. Returns the URL."""
    fn = os.path.basename(local_path)
    url = public_url(fn)
    if url_ok(url):
        return url
    ensure_release()
    log(f"uploading {fn} to release {TAG}")
    r = _run(["gh", "release", "upload", TAG, "-R", REPO, local_path, "--clobber"])
    if r.returncode != 0:
        raise RuntimeError(f"gh release upload failed: {r.stderr[:300]}")
    if not url_ok(url):
        raise RuntimeError(f"asset uploaded but {url} is not fetchable")
    return url
