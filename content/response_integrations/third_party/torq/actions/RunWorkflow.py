# Actions/RunWorkflow.py

import json
import base64
from datetime import datetime, date
from typing import Any, Dict, Optional, List

from SiemplifyAction import SiemplifyAction
from SiemplifyUtils import output_handler
from TorqManager import TorqManager, TorqConfig

PROVIDER   = "Torq"
ACTION_UI  = "Run Workflow"
SOURCE_STR = "Google SecOps"
TORQ_LABEL = "run_workflow"


# ---------------- JSON helpers ----------------
def _json_default(o: Any):
    if isinstance(o, (datetime, date)):
        return o.isoformat()
    if isinstance(o, (bytes, bytearray, memoryview)):
        return base64.b64encode(bytes(o)).decode("ascii")
    if isinstance(o, (set, tuple)):
        return list(o)
    return str(o)


def _json_sanitize(obj: Any):
    """Safe JSON conversion for complex objects."""
    return json.loads(json.dumps(obj, default=_json_default))


# ---------------- config & param readers ----------------
def _ci_instance_params(si) -> tuple:
    """
    Reads integration instance fields (case-insensitive labels):
      Torq URL, Webhook Secret, Region, Client ID/Secret (optional),
      Torq API Base URL (optional), Token URL (optional), Bearer Token (override) (optional).
    """
    raw = si.get_configuration(PROVIDER) or {}
    lower = {(k or "").strip().lower(): v for k, v in raw.items()}

    url = lower.get("torq url") or lower.get("webhook url") or lower.get("url")
    secret = lower.get("webhook secret") or lower.get("secret") or lower.get("token")
    region = (lower.get("region") or "US").strip().upper()

    client_id = lower.get("client id") or lower.get("client_id") or lower.get("clientid")
    client_secret = lower.get("client secret") or lower.get("client_secret") or lower.get("clientsecret")

    api_base_url = lower.get("torq api base url") or lower.get("api base url") or lower.get("api_base_url")
    token_url = lower.get("token url") or lower.get("token_url")

    bearer_override = lower.get("bearer token (override)") or lower.get("bearer token") or None

    return url, secret, region, client_id, client_secret, api_base_url, token_url, bearer_override


def _ci_action_params(si) -> tuple:
    """
    Reads action parameters (case-insensitive):
      workflow_input (JSON), Include Alert Payload (bool),
      Poll Max Seconds (optional), Poll Interval Seconds (optional).
    """
    params_raw = getattr(si, "parameters", {}) or {}
    lower = {(k or "").strip().lower(): v for k, v in params_raw.items()}

    # workflow_input
    wfi_raw = params_raw.get("workflow_input", params_raw.get("Workflow_Input", "{}"))
    if isinstance(wfi_raw, dict):
        workflow_input = wfi_raw
    else:
        s = (wfi_raw or "").strip()
        workflow_input = json.loads(s) if s else {}

    if not isinstance(workflow_input, dict):
        raise ValueError("workflow_input must be a JSON object.")

    # Include Alert Payload
    inc_alert_raw = lower.get("include alert payload", "false")
    include_alert = _to_bool(inc_alert_raw)

    # Poll timings
    try:
        poll_max = float(lower.get("poll max seconds")) if lower.get("poll max seconds") else None
    except Exception:
        poll_max = None
    try:
        poll_ivl = float(lower.get("poll interval seconds")) if lower.get("poll interval seconds") else None
    except Exception:
        poll_ivl = None

    return workflow_input, include_alert, poll_max, poll_ivl


def _to_bool(val, default=False) -> bool:
    if isinstance(val, bool):
        return val
    s = str(val).strip().lower()
    if s in ("true", "1", "yes", "y", "on"):
        return True
    if s in ("false", "0", "no", "n", "off"):
        return False
    return bool(default)


# ---------------- context & alert serialization ----------------
def _maybe_min_context(si) -> Dict[str, Any]:
    """Minimal case/environment context; never raises."""
    ctx: Dict[str, Any] = {}
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

    env = getattr(si, "environment", None)
    ctx["environment"] = env if env else "Default Environment"
    return ctx


def _collect_alert(si) -> Dict[str, Any]:
    """
    Best-effort alert dict extraction. Prefers si.current_alert; falls back to first case alert.
    Includes common fields + entities subset. Safe for JSON.
    """
    alert = None
    try:
        alert = getattr(si, "current_alert", None)
    except Exception:
        alert = None

    if not alert:
        try:
            case = getattr(si, "case", None)
            alerts = getattr(case, "alerts", None)
            if alerts:
                alert = alerts[0]
        except Exception:
            alert = None

    if not alert:
        return {}

    blob: Dict[str, Any] = {}
    try:
        blob["identifier"] = getattr(alert, "identifier", None) or getattr(alert, "alert_identifier", None) or getattr(alert, "id", None)
        blob["name"] = getattr(alert, "name", None) or getattr(alert, "rule_generator", None)
        blob["vendor"] = getattr(alert, "vendor", None)
        blob["product"] = getattr(alert, "product", None)
        blob["severity"] = getattr(alert, "severity", None) or getattr(alert, "priority", None)
        blob["start_time"] = getattr(alert, "start_time", None)
        blob["end_time"] = getattr(alert, "end_time", None)
        blob["description"] = getattr(alert, "description", None)
        blob["additional_properties"] = getattr(alert, "additional_properties", None) or getattr(alert, "raw_data", None)

        ents: List[Dict[str, Any]] = []
        try:
            for e in getattr(alert, "entities", []) or []:
                ents.append({
                    "identifier": getattr(e, "identifier", None),
                    "entity_type": getattr(e, "entity_type", None) or getattr(e, "type", None),
                    "is_suspected": getattr(e, "is_suspected", None) or getattr(e, "is_suspect", None),
                    "additional_properties": getattr(e, "additional_properties", None),
                })
        except Exception:
            pass
        if ents:
            blob["entities"] = ents
    except Exception:
        pass

    return _json_sanitize(blob)


# ---------------- main ----------------
@output_handler
def main():
    si = SiemplifyAction()
    logger = getattr(si, "LOGGER", None)
    si.script_name = f"{PROVIDER} - {ACTION_UI}"
    si.LOGGER.info("Reading configuration from Server")

    # Integration config
    url, secret, region, client_id, client_secret, api_base, token_url, bearer_override = _ci_instance_params(si)
    if not url:
        si.end("Missing required integration parameter: Torq URL", False)
        return
    if not secret:
        si.end("Missing required integration parameter: Webhook Secret", False)
        return

    # Action params
    workflow_input, include_alert, poll_max, poll_ivl = _ci_action_params(si)

    # Manager config
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
        prefer_public_api=True,   # Public API polling (curl parity)
        ignore_env_proxy=True,    # avoid proxy header stripping
        bearer_override=bearer_override,
    )
    mgr = TorqManager(cfg, logger=logger)

    # Build Torq request
    payload: Dict[str, Any] = {
        "label": TORQ_LABEL,
        "source": SOURCE_STR,
        "context": _maybe_min_context(si),
        "workflow_input": workflow_input,
    }
    if include_alert:
        alert_blob = _collect_alert(si)
        if alert_blob:
            payload["alert"] = alert_blob

    payload = _json_sanitize(payload)

    # Invoke Torq & poll
    result_blob: Dict[str, Any] = {"request": payload}
    try:
        resp = mgr.run_workflow(
            payload,
            correlation_id=None,
            idempotency_key=None,
            poll_max_seconds=poll_max if poll_max is not None else None,
            poll_interval_seconds=poll_ivl if poll_ivl is not None else None,
        )

        # Normalize response for SIEMPLIFY result pane
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

        # Human-readable end message
        status_code = resp.get("status_code")
        final_status = (final_json.get("status") or "").upper() if isinstance(final_json, dict) else ""
        exec_id = exec_info.get("id")

        msg_bits = [f"status={status_code}", "async=True"]
        if exec_id:
            msg_bits.append(f"execution_id={exec_id}")
        if final_status:
            msg_bits.append(f"final_status={final_status}")

        ok = bool(status_code and 200 <= int(status_code) < 300)
        si.end(f'Torq run_workflow requested ({", ".join(msg_bits)}).', ok)

    except Exception as e:
        if logger:
            logger.exception(f"[{ACTION_UI}] failed: {e}")
        result_blob["error"] = str(e)
        si.result.add_result_json(result_blob)
        si.end(f"Failed to request run_workflow in Torq: {e}", False)


if __name__ == "__main__":
    main()