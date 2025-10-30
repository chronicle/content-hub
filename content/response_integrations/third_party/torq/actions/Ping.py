# Actions/Ping.py

import json
import base64
from datetime import datetime, date
from SiemplifyAction import SiemplifyAction
from SiemplifyUtils import output_handler
from TorqManager import TorqManager, TorqConfig

PROVIDER = "Torq"
ACTION_UI = "Ping"
TORQ_ACTION = "ping"
SOURCE_STR = "Google SecOps"


def _json_default(o):
    if isinstance(o, (datetime, date)):
        return o.isoformat()
    if isinstance(o, (set, tuple)):
        return list(o)
    if isinstance(o, (bytes, bytearray, memoryview)):
        return base64.b64encode(bytes(o)).decode("ascii")
    return str(o)


def _json_sanitize(obj):
    return json.loads(json.dumps(obj, default=_json_default))


def _ci_instance_params(si):
    raw = si.get_configuration(PROVIDER) or {}
    lower = {(k or "").strip().lower(): v for k, v in raw.items()}

    url = lower.get("torq url") or lower.get("webhook url") or lower.get("url")
    secret = lower.get("webhook secret") or lower.get("secret") or lower.get("token")
    region = (lower.get("region") or "US").strip().upper()

    client_id = lower.get("client id") or lower.get("client_id")
    client_secret = lower.get("client secret") or lower.get("client_secret")

    api_base_url = lower.get("torq api base url") or lower.get("api base url") or lower.get("api_base_url")
    token_url = lower.get("token url") or lower.get("token_url")

    bearer_override = lower.get("bearer token (override)") or lower.get("bearer token") or None

    return url, secret, region, client_id, client_secret, api_base_url, token_url, bearer_override


def _ci_action_params(si):
    raw = getattr(si, "parameters", {}) or {}
    lower = {(k or "").strip().lower(): v for k, v in raw.items()}

    try:
        poll_max = float(lower.get("poll max seconds")) if lower.get("poll max seconds") else None
    except Exception:
        poll_max = None

    try:
        poll_ivl = float(lower.get("poll interval seconds")) if lower.get("poll interval seconds") else None
    except Exception:
        poll_ivl = None

    return poll_max, poll_ivl


def _maybe_min_context(si):
    ctx = {}
    try:
        cid = getattr(getattr(si, "current_case", None), "identifier", None) or getattr(getattr(si, "case", None), "case_id", None)
        if cid:
            ctx["case_id"] = cid
    except Exception:
        pass
    try:
        cname = getattr(getattr(si, "current_case", None), "name", None) or getattr(getattr(si, "case", None), "case_name", None)
        if cname:
            ctx["case_name"] = cname
    except Exception:
        pass
    try:
        env = getattr(si, "environment", None)
        if env:
            ctx["environment"] = env
    except Exception:
        pass
    if "environment" not in ctx:
        ctx["environment"] = "Default Environment"
    return ctx


@output_handler
def main():
    si = SiemplifyAction()
    logger = getattr(si, "LOGGER", None)
    si.script_name = f"{PROVIDER} - {ACTION_UI}"
    si.LOGGER.info("Reading configuration from Server")

    url, secret, region, client_id, client_secret, api_base, token_url, bearer_override = _ci_instance_params(si)
    if not url:
        si.end("Missing required integration parameter: Torq URL", False)
        return
    if not secret:
        si.end("Missing required integration parameter: Webhook Secret", False)
        return

    poll_max, poll_ivl = _ci_action_params(si)

    cfg = TorqConfig(
        webhook_url=url,
        secret=secret,
        region=region,
        client_id=client_id,
        client_secret=client_secret,
        api_base_url=api_base,
        token_url=token_url,
        verify_ssl=True,
        timeout=15,
        https_proxy=None,
        async_mode=True,
        read_timeout_s=0.25,
        poll_max_seconds=60.0,
        poll_interval_seconds=3.0,
        prefer_public_api=True,   # curl-parity polling
        ignore_env_proxy=True,    # avoid env proxy interference
        bearer_override=bearer_override,
    )
    mgr = TorqManager(cfg, logger=logger)

    payload = _json_sanitize({
        "source": SOURCE_STR,
        "action": TORQ_ACTION,
        "label": "ping",
        "context": _maybe_min_context(si),
    })

    result_blob = {"request": payload}

    try:
        resp = mgr.run_workflow(
            payload,
            correlation_id=None,
            idempotency_key=None,
            poll_max_seconds=poll_max if poll_max is not None else None,
            poll_interval_seconds=poll_ivl if poll_ivl is not None else None,
        )

        result_blob["response"] = {
            "status_code": resp.get("status_code"),
            "headers": resp.get("headers"),
            "content_type": resp.get("content_type"),
            "json": resp.get("json"),
            "text": resp.get("text"),
        }
        result_blob["async"] = True

        exec_info = (resp or {}).get("execution") or {}
        final_json = exec_info.get("final") if isinstance(exec_info, dict) else None

        if exec_info.get("id"):
            result_blob["execution_id"] = exec_info["id"]
        if isinstance(final_json, dict):
            result_blob["execution_final"] = final_json
            out = final_json.get("output") if isinstance(final_json.get("output"), dict) else None
            if out:
                result_blob["output"] = out

        si.result.add_result_json(result_blob)

        status_code = resp.get("status_code")
        final_status = (final_json.get("status") or "").upper() if isinstance(final_json, dict) else ""
        exec_id = exec_info.get("id")
        msg_bits = [f"status={status_code}", "async=True"]
        if exec_id:
            msg_bits.append(f"execution_id={exec_id}")
        if final_status:
            msg_bits.append(f"final_status={final_status}")

        ok = bool(status_code and 200 <= int(status_code) < 300)
        si.end(f'Torq ping requested ({", ".join(msg_bits)}).', ok)

    except Exception as e:
        if logger:
            logger.exception(f"[{ACTION_UI}] failed: {e}")
        result_blob["error"] = str(e)
        si.result.add_result_json(result_blob)
        si.end(f"Failed to send ping to Torq: {e}", False)


if __name__ == "__main__":
    main()