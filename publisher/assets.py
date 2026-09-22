"""Public video URLs via GitHub release assets. Meta must be able to fetch
the URL; it cannot take a local file, and a Composio s3key needs a prior
Composio action, so releases are the cheap way to host these."""
import os, subprocess, time
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


def url_ok(url, tries=1, delay=6):
    """A freshly uploaded asset can take a few seconds to become fetchable,
    so callers that have just uploaded should pass tries>1."""
    for i in range(tries):
        try:
            r = requests.get(url, headers={"Range": "bytes=0-0"}, timeout=60,
                             allow_redirects=True)
            if r.status_code in (200, 206):
                return True
        except requests.RequestException:
            pass
        if i < tries - 1:
            time.sleep(delay)
    return False


def existing_assets():
    """Names already on the release, from the API.

    Do NOT probe the download URL to test existence: GitHub's CDN caches the
    404 for a URL that does not exist yet, and that cached 404 then survives
    the upload, leaving an asset that is state=uploaded but unfetchable.
    """
    r = _run(["gh", "api", f"repos/{REPO}/releases/tags/{TAG}",
              "-q", ".assets[].name"])
    if r.returncode != 0:
        return set()
    return {ln.strip() for ln in r.stdout.splitlines() if ln.strip()}


def ensure_uploaded(local_path, log, known=None):
    """Upload the asset if it is not already on the release. Returns the URL."""
    fn = os.path.basename(local_path)
    url = public_url(fn)
    present = known if known is not None else existing_assets()
    if fn in present:
        return url
    ensure_release()
    log(f"uploading {fn} to release {TAG}")
    r = _run(["gh", "release", "upload", TAG, "-R", REPO, local_path, "--clobber"])
    if r.returncode != 0:
        raise RuntimeError(f"gh release upload failed: {r.stderr[:300]}")
    if not url_ok(url, tries=8, delay=15):
        # not fatal: the asset is on the release and the worker re-checks
        # before posting. Only a cached negative should cause this.
        log(f"WARNING: {fn} uploaded but not fetchable yet")
    return url
