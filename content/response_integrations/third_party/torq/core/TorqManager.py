# TorqManager.py

import json
import time
import uuid
import base64
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple
from datetime import datetime, date

import requests
from requests import Timeout, ConnectionError, ReadTimeout

# Optional shared errors; safe fallbacks if not present
try:
    from TorqErrors import (
        TorqError,
        TorqAuthError,
        TorqRateLimitError,
        TorqServerError,
        TorqClientError,
    )
except Exception:
    class TorqError(Exception): ...
    class TorqAuthError(TorqError): ...
    class TorqRateLimitError(TorqError): ...
    class TorqServerError(TorqError): ...
    class TorqClientError(TorqError): ...

# ---------- helpers ----------
def _json_default(o):
    if isinstance(o, (datetime, date)):
        return o.isoformat()
    if isinstance(o, (set, tuple)):
        return list(o)
    if isinstance(o, (bytes, bytearray, memoryview)):
        return base64.b64encode(bytes(o)).decode("ascii")
    return str(o)

_REGION = {
    "US": {
        "api_base": "https://api.torq.io/v1alpha",
        "public_api_base": "https://api.torq.io/public/v1alpha",
        "token_url": "https://auth.torq.io/v1/auth/token",
    },
    "EU": {
        "api_base": "https://api.eu.torq.io/v1alpha",
        "public_api_base": "https://api.eu.torq.io/public/v1alpha",
        "token_url": "https://auth.eu.torq.io/v1/auth/token",
    },
}

@dataclass
class TorqConfig:
    # Required
    webhook_url: str
    secret: str
    region: str  # "US" or "EU"

    # Optional OAuth to mint bearer (for polling) — OR use bearer_override
    client_id: Optional[str] = None
    client_secret: Optional[str] = None

    # Optional overrides
    api_base_url: Optional[str] = None           # workspace API (not used by default)
    public_api_base_url: Optional[str] = None    # defaults by region
    token_url: Optional[str] = None

    # Networking/behavior
    verify_ssl: bool = True
    timeout: int = 15
    https_proxy: Optional[str] = None
    max_retries: int = 3
    backoff_base: float = 0.6
    extra_headers: Optional[Dict[str, str]] = None
    async_mode: bool = True
    read_timeout_s: float = 0.25

    # Polling
    poll_max_seconds: float = 60.0
    poll_interval_seconds: float = 3.0

    # Curl-parity flags
    prefer_public_api: bool = True       # default to public API (your curl path)
    ignore_env_proxy: bool = True        # bypass env proxies when polling
    bearer_override: Optional[str] = None  # paste a bearer to force polling with it


class TorqManager:
    def __init__(self, cfg: TorqConfig, logger=None):
        self.cfg = cfg
        self.session = requests.Session()
        self.logger = logger

        region = (cfg.region or "US").strip().upper()
        defaults = _REGION.get(region, _REGION["US"])
        if not self.cfg.api_base_url:
            self.cfg.api_base_url = defaults["api_base"]
        if not self.cfg.public_api_base_url:
            self.cfg.public_api_base_url = defaults["public_api_base"]
        if not self.cfg.token_url:
            self.cfg.token_url = defaults["token_url"]

        # Apply proxy settings
        if cfg.https_proxy:
            self.session.proxies.update({"https": cfg.https_proxy})

        # Curl parity: ignore env proxies for polling calls
        try:
            self.session.trust_env = not self.cfg.ignore_env_proxy
            if self.cfg.ignore_env_proxy:
                self.session.proxies.clear()
        except Exception:
            pass

        # Token cache (if minting via client_credentials)
        self._oauth_token: Optional[str] = None
        self._token_expiry_ts: float = 0.0
        self._token_skew: float = 60.0

    # ---------------- Public API: run + poll ----------------
    def run_workflow(
        self,
        payload: Dict[str, Any],
        correlation_id: Optional[str] = None,
        idempotency_key: Optional[str] = None,
        poll_max_seconds: Optional[float] = None,
        poll_interval_seconds: Optional[float] = None,
    ) -> Dict[str, Any]:
        """POST webhook, then poll execution via Public API (curl-parity) by default."""
        try:
            status, text, resp_json, headers, ctype = self._post_json(
                payload, correlation_id=correlation_id, idempotency_key=idempotency_key
            )
        except Exception as e:
            return {"status_code": 0, "text": str(e), "json": None, "headers": {}, "content_type": ""}

        result = {
            "status_code": status,
            "headers": headers,
            "content_type": ctype,
            "text": text if text and not resp_json else None,
            "json": resp_json,
        }

        # execution id (handle multiple shapes)
        exec_id = self._extract_execution_id(resp_json, headers)

        ex: Dict[str, Any] = {"id": exec_id, "polled": False, "final": None}
        result["execution"] = ex

        if not exec_id:
            ex["skip_reason"] = "no execution_id in webhook response"
            return result

        # pick bearer
        token = None
        if self.cfg.bearer_override:
            token = f"Bearer {self.cfg.bearer_override}"
        else:
            token = self._get_token()

        poll_max = poll_max_seconds if poll_max_seconds is not None else self.cfg.poll_max_seconds
        poll_ivl = poll_interval_seconds if poll_interval_seconds is not None else self.cfg.poll_interval_seconds

        final = self._poll_execution_public_exact(
            execution_id=exec_id,
            max_seconds=poll_max,
            interval_seconds=poll_ivl,
            token=token,
        )
        ex["polled"] = True
        ex["final"] = final

        # Output surfacing
        out, path = self._extract_output(final if isinstance(final, dict) else {})
        ex["final_output"] = out
        ex["final_output_path"] = path

        return result

    # ---------------- Webhook POST ----------------
    def _post_json(
        self,
        payload: Dict[str, Any],
        correlation_id: Optional[str] = None,
        idempotency_key: Optional[str] = None,
    ) -> Tuple[int, Optional[str], Optional[Dict[str, Any]], Dict[str, str], str]:
        url = (self.cfg.webhook_url or "").rstrip("/")
        if not url:
            raise TorqClientError("Missing Webhook URL")
        if not correlation_id:
            correlation_id = str(uuid.uuid4())

        headers = self._headers(correlation_id, idempotency_key)

        attempt = 0
        last_exc = None
        while attempt <= self.cfg.max_retries:
            try:
                if self.logger:
                    self.logger.info(f"[Torq] POST {url} attempt {attempt+1}/{self.cfg.max_retries+1} corr={correlation_id}")

                timeouts = (
                    self.cfg.timeout,
                    self.cfg.read_timeout_s if self.cfg.async_mode else self.cfg.timeout,
                )
                resp = self.session.post(
                    url,
                    data=json.dumps(payload, default=_json_default),
                    headers=headers,
                    verify=self.cfg.verify_ssl,
                    timeout=timeouts,
                )
                status = resp.status_code
                resp_headers = dict(resp.headers or {})
                ctype = resp_headers.get("Content-Type", "") or resp_headers.get("content-type", "") or ""
                text = resp.text or None
                resp_json = self._maybe_parse_json(text, ctype)

                if status in (401, 403):
                    raise TorqAuthError("Webhook auth error (check `Webhook Secret`).")
                if status == 429:
                    if attempt < self.cfg.max_retries:
                        self._sleep(attempt); attempt += 1; continue
                    raise TorqRateLimitError("Rate limited (429)")
                if 500 <= status <= 599:
                    if attempt < self.cfg.max_retries:
                        self._sleep(attempt); attempt += 1; continue
                    raise TorqServerError(f"Server error {status}")
                if 400 <= status <= 499:
                    raise TorqClientError(f"Client error {status}: {text}")

                return status, text, resp_json, resp_headers, ctype

            except ReadTimeout:
                if self.cfg.async_mode:
                    if self.logger: self.logger.info("[Torq] Async read-timeout; assuming 202/accepted.")
                    return 202, "assumed async (read timeout)", None, {}, ""
                last_exc = "read timeout"
            except (Timeout, ConnectionError) as e:
                last_exc = e
                if attempt < self.cfg.max_retries:
                    self._sleep(attempt); attempt += 1; continue
                raise TorqError(f"Network error after retries: {e}") from e
            except TorqError:
                raise
            except Exception as e:
                last_exc = e
                if attempt < self.cfg.max_retries:
                    self._sleep(attempt); attempt += 1; continue
                raise TorqError(f"Unexpected error after retries: {e}") from e

        raise TorqError(f"Exited retry loop unexpectedly: {last_exc}")

    def _headers(self, correlation_id: Optional[str], idempotency_key: Optional[str]) -> Dict[str, str]:
        h = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/plain, */*",
            "User-Agent": "TorqWebhookClient/1.0",
            "X-Integration-Name": "Torq Webhook (SOAR)",
            "X-Integration-Version": "3.0.0",
        }
        # webhook auth header is literally "secret"
        raw = (self.cfg.secret or "").strip().strip('"').strip("'")
        if self.logger:
            self.logger.info(f"[Torq] Webhook auth header 'secret' (len={len(raw)})")
        h["secret"] = raw

        if correlation_id:
            h["X-Correlation-ID"] = correlation_id
        if idempotency_key:
            h["X-Idempotency-Key"] = idempotency_key
        if self.cfg.extra_headers:
            h.update(self.cfg.extra_headers)
        return h

    # ---------------- Public API poller (curl parity) ----------------
    def _poll_execution_public_exact(
        self,
        execution_id: str,
        max_seconds: float,
        interval_seconds: float,
        token: Optional[str],
    ) -> Optional[Dict[str, Any]]:
        """
        EXACT match to your working curl:
          GET {public_api_base_url}/executions/{id}
          Headers: Authorization: Bearer <token>, Accept: application/json
          No redirects, proxy bypass (via session flags in __init__)
        Returns full JSON; terminal when status in SUCCESS/FAILED/STOPPED/DROPPED/UNKNOWN.
        """
        base = (self.cfg.public_api_base_url or "").rstrip("/")
        if not base:
            return {"error": "public_api_base_url not set", "_api_surface": "public"}
        if not token:
            return {"error": "no bearer token for public API polling", "_api_surface": "public"}

        tok = str(token).strip()
        if not tok.lower().startswith("bearer "):
            tok = f"Bearer {tok}"

        url = f"{base}/executions/{execution_id}"
        start = time.time()
        last = None

        while (time.time() - start) < max_seconds:
            try:
                if self.logger:
                    self.logger.info(f"[Torq] Poll {url} (public)")
                r = self.session.get(
                    url,
                    headers={"Authorization": tok, "Accept": "application/json"},
                    verify=self.cfg.verify_ssl,
                    timeout=self.cfg.timeout,
                    allow_redirects=False,  # expose 3xx if any
                )
                payload: Dict[str, Any] = {
                    "_status_code": r.status_code,
                    "_headers": dict(r.headers or {}),
                    "_url": url,
                    "_api_surface": "public",
                }
                # Parse JSON body if possible
                try:
                    j = r.json()
                    if isinstance(j, dict):
                        payload.update(j)
                except Exception:
                    payload["_raw_text"] = (r.text or "")[:2000]

                # Terminal by documented statuses; else stop on non-2xx
                status = (payload.get("status") or "").upper()
                if status in {"SUCCESS", "FAILED", "STOPPED", "DROPPED", "EXECUTION_STATUS_UNKNOWN"}:
                    return payload
                if r.status_code < 200 or r.status_code >= 300:
                    return payload

                last = payload
                time.sleep(max(0.2, interval_seconds))
            except Exception as e:
                return {"error": str(e), "_url": url, "_api_surface": "public"}

        return last

    # ---------------- OAuth (client_credentials) ----------------
    def _get_token(self, force_refresh: bool = False) -> Optional[str]:
        """Mint/reuse 'Bearer <token>' from auth(.eu).torq.io; used if no bearer_override."""
        now = time.time()
        if not force_refresh:
            if self._oauth_token and (now + self._token_skew) < self._token_expiry_ts:
                if self.logger:
                    self.logger.info("[Torq] Reusing OAuth token (cached).")
                return self._oauth_token
        if not (self.cfg.client_id and self.cfg.client_secret and self.cfg.token_url):
            return None

        if self.logger:
            self.logger.info("[Torq] Requesting OAuth token (client_credentials).")

        try:
            r = self.session.post(
                self.cfg.token_url,
                data={"grant_type": "client_credentials"},
                headers={
                    "Accept": "application/json",
                    "Accept-Language": "en_US",
                    "Content-Type": "application/x-www-form-urlencoded",
                    "User-Agent": "TorqWebhookClient/1.0",
                },
                auth=(self.cfg.client_id, self.cfg.client_secret),
                timeout=self.cfg.timeout,
                verify=self.cfg.verify_ssl,
            )
            if not (200 <= r.status_code < 300):
                if self.logger:
                    self.logger.warning(f"[Torq] Token request failed ({r.status_code}): {r.text}")
                return None
            j = r.json()
            access_token = j.get("access_token")
            token_type = (j.get("token_type") or "Bearer").title()
            expires_in = float(j.get("expires_in") or 3600)
            if access_token:
                self._oauth_token = f"{token_type} {access_token}"
                self._token_expiry_ts = time.time() + expires_in
                if self.logger:
                    self.logger.info(f"[Torq] Token acquired (type={token_type}, ttl≈{int(expires_in)}s).")
                return self._oauth_token
            if self.logger:
                self.logger.warning(f"[Torq] Token JSON missing access_token: {j}")
            return None
        except Exception as e:
            if self.logger:
                self.logger.warning(f"[Torq] Token request exception: {e}")
            return None

    # ---------------- misc utils ----------------
    @staticmethod
    def _maybe_parse_json(text: Optional[str], content_type: str):
        if not text:
            return None
        ct = (content_type or "").lower()
        looks_json = ct.startswith("application/json") or text.lstrip().startswith(("{", "["))
        if not looks_json:
            return None
        try:
            return json.loads(text)
        except Exception:
            return None

    def _sleep(self, attempt: int) -> None:
        time.sleep(self.cfg.backoff_base * (2 ** attempt))

    def _extract_execution_id(self, resp_json: Optional[Dict[str, Any]], headers: Dict[str, str]) -> Optional[str]:
        """
        Support multiple possible webhook response shapes:
          { "execution_id": "..." }
          { "run_id": "..." }
          { "id": "..." }
        And header fallback: X-Execution-Id (if Torq ever adds it)
        """
        if isinstance(resp_json, dict):
            for k in ("execution_id", "run_id", "id"):
                v = resp_json.get(k)
                if isinstance(v, str) and v.strip():
                    return v.strip()
        # header fallback
        try:
            x = headers.get("X-Execution-Id") or headers.get("x-execution-id")
            if x and str(x).strip():
                return str(x).strip()
        except Exception:
            pass
        return None

    def _extract_output(self, js: Dict[str, Any]):
        """Return (output, path). Tries common locations."""
        if not isinstance(js, dict):
            return None, None
        if "output" in js and js["output"] is not None:
            return js["output"], "output"
        for a, b in (("result", "output"), ("data", "output"),
                     ("execution", "output"), ("payload", "output")):
            try:
                v = js.get(a)
                if isinstance(v, dict) and v.get(b) is not None:
                    return v.get(b), f"{a}.{b}"
            except Exception:
                pass
        if "_extracted_output" in js:
            return js.get("_extracted_output"), js.get("_extracted_output_path")
        return None, None