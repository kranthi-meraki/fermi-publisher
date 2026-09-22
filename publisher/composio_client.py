"""Composio access over MCP.

The dashboard key (ck_...) authenticates MCP clients via the
`x-consumer-api-key` header against https://connect.composio.dev/mcp. It is
NOT a platform REST key: backend.composio.dev rejects it outright. So this
client speaks JSON-RPC to the MCP endpoint and drives the same
COMPOSIO_MULTI_EXECUTE_TOOL / COMPOSIO_REMOTE_WORKBENCH meta-tools an
interactive session would.
"""
import json, os, time
import requests

ENDPOINT = os.environ.get("COMPOSIO_MCP_URL", "https://connect.composio.dev/mcp")
PROTOCOL = "2025-06-18"


class ComposioError(RuntimeError):
    pass


class Composio:
    def __init__(self, api_key=None, timeout=300):
        self.key = api_key or os.environ["COMPOSIO_API_KEY"]
        self.timeout = timeout
        self.sid = None
        self._id = 0
        self._connect()

    # ---------- transport ----------
    def _headers(self):
        h = {"x-consumer-api-key": self.key,
             "Content-Type": "application/json",
             "Accept": "application/json, text/event-stream"}
        if self.sid:
            h["mcp-session-id"] = self.sid
        return h

    def _rpc(self, method, params=None, notify=False):
        self._id += 1
        body = {"jsonrpc": "2.0", "method": method}
        if not notify:
            body["id"] = self._id
        if params is not None:
            body["params"] = params
        r = requests.post(ENDPOINT, headers=self._headers(), json=body,
                          timeout=self.timeout)
        if r.headers.get("mcp-session-id"):
            self.sid = r.headers["mcp-session-id"]
        if notify:
            return None
        if r.status_code >= 400:
            raise ComposioError(f"MCP {method} http {r.status_code}: {r.text[:300]}")
        out = None
        for line in r.text.splitlines():          # SSE framing
            if line.startswith("data: "):
                out = json.loads(line[6:])
        if out is None:
            try:
                out = r.json()
            except ValueError:
                raise ComposioError(f"MCP {method}: unparseable response {r.text[:300]}")
        if "error" in out:
            raise ComposioError(f"MCP {method}: {str(out['error'])[:300]}")
        return out.get("result")

    def _connect(self):
        self.sid = None
        self._rpc("initialize", {"protocolVersion": PROTOCOL, "capabilities": {},
                                 "clientInfo": {"name": "fermi-publisher",
                                                "version": "1.0"}})
        self._rpc("notifications/initialized", notify=True)

    def _call(self, name, arguments, retries=2):
        last = None
        for attempt in range(retries + 1):
            try:
                res = self._rpc("tools/call", {"name": name, "arguments": arguments})
            except (ComposioError, requests.RequestException) as e:
                last = str(e)
                if "session" in last.lower() or "404" in last:
                    self._connect()          # session expired; re-handshake once
                time.sleep(2 ** attempt)
                continue
            content = (res or {}).get("content") or []
            if not content:
                raise ComposioError(f"{name}: empty content")
            text = content[0].get("text", "")
            try:
                return json.loads(text)
            except ValueError:
                return {"raw": text}
        raise ComposioError(f"{name} unreachable: {last}")

    # ---------- public ----------
    def execute(self, tool_slug, arguments, account, thought="publish", step="RUN"):
        """Run one Composio tool. Raises ComposioError if it did not succeed."""
        env = self._call("COMPOSIO_MULTI_EXECUTE_TOOL", {
            "sync_response_to_workbench": False,
            "thought": thought, "current_step": step,
            "tools": [{"tool_slug": tool_slug, "account": account,
                       "arguments": arguments}]})
        results = (env.get("data") or {}).get("results") or []
        if not results:
            raise ComposioError(f"{tool_slug}: no result ({str(env)[:200]})")
        r = results[0]
        resp = r.get("response") or {}
        if not resp.get("successful"):
            raise ComposioError(f"{tool_slug} failed: "
                                f"{str(resp.get('error') or resp.get('data'))[:400]}")
        return resp.get("data") or {}

    def workbench(self, code, thought="run", step="RUN"):
        """Run Python in Composio's sandbox. Used for YouTube uploads, which
        need an s3key that only a prior Composio action can mint."""
        env = self._call("COMPOSIO_REMOTE_WORKBENCH", {
            "code_to_execute": code, "thought": thought, "current_step": step})
        data = env.get("data") or env
        if data.get("error"):
            raise ComposioError(f"workbench: {str(data['error'])[:400]}")
        return data.get("stdout", "")
