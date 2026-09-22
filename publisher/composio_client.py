"""Thin REST adapter for Composio v3. One place to change if the API moves."""
import hashlib, os, time
import requests

BASE = "https://backend.composio.dev/api/v3"


class ComposioError(RuntimeError):
    pass


class Composio:
    def __init__(self, api_key=None, timeout=180):
        self.key = api_key or os.environ["COMPOSIO_API_KEY"]
        self.timeout = timeout
        self.s = requests.Session()
        self.s.headers.update({"x-api-key": self.key, "Content-Type": "application/json"})

    def execute(self, tool_slug, arguments, connected_account_id, retries=2):
        """Execute a tool. Raises ComposioError on a failed envelope.

        NOTE: retries here are for TRANSPORT failures only. A publish that
        times out may still have succeeded, so callers that publish must
        check remote state themselves before calling again.
        """
        url = f"{BASE}/tools/execute/{tool_slug}"
        body = {"connected_account_id": connected_account_id, "arguments": arguments}
        last = None
        for attempt in range(retries + 1):
            try:
                r = self.s.post(url, json=body, timeout=self.timeout)
            except requests.RequestException as e:
                last = f"transport: {e}"
                time.sleep(2 ** attempt)
                continue
            if r.status_code >= 500:
                last = f"http {r.status_code}: {r.text[:300]}"
                time.sleep(2 ** attempt)
                continue
            try:
                env = r.json()
            except ValueError:
                raise ComposioError(f"non-json response {r.status_code}: {r.text[:300]}")
            if not env.get("successful"):
                err = env.get("error") or env.get("data") or {}
                raise ComposioError(f"{tool_slug} failed: {str(err)[:400]}")
            return env.get("data") or {}
        raise ComposioError(f"{tool_slug} unreachable: {last}")

    def upload_file(self, path, toolkit_slug, tool_slug):
        """Upload a local file and return the {name, mimetype, s3key} dict
        that a file_uploadable tool parameter expects."""
        name = os.path.basename(path)
        mimetype = "video/mp4"
        md5 = hashlib.md5(open(path, "rb").read()).hexdigest()
        r = self.s.post(f"{BASE}/files/upload/request", json={
            "toolkit_slug": toolkit_slug, "tool_slug": tool_slug,
            "filename": name, "mimetype": mimetype, "md5": md5}, timeout=60)
        r.raise_for_status()
        info = r.json()
        key = info.get("key")
        put_url = info.get("new_presigned_url") or info.get("presigned_url")
        if not (key and put_url):
            raise ComposioError(f"unexpected upload-request response: {str(info)[:300]}")
        with open(path, "rb") as fh:
            up = requests.put(put_url, data=fh, headers={"Content-Type": mimetype}, timeout=600)
        if up.status_code not in (200, 201, 204):
            raise ComposioError(f"presigned PUT failed {up.status_code}: {up.text[:200]}")
        return {"name": name, "mimetype": mimetype, "s3key": key}
