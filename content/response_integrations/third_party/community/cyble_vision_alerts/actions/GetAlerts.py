"""
GetAlerts — manual on-demand alert fetch action.

Useful for:
  - Analyst-triggered ad-hoc pulls (e.g., "get latest phishing alerts for this domain").
  - Playbook enrichment steps.
  - Testing the integration without waiting for the job cycle.

Parameters:
  - Services        (comma-separated service names)
  - Hours Back      (default 24)
  - Max Results     (default 50)
  - Statuses        (comma-separated, default: all active)
"""
from __future__ import annotations

from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from datetime import datetime, timezone, timedelta
import json

from ..core.CybleManager import CybleManager, CybleAuthError, CybleAPIError
from ..core.CybleAlertMapper import CybleAlertMapper
from ..core.constants import (
    INTEGRATION_NAME,
    PARAM_API_KEY,
    PARAM_BASE_URL,
    PARAM_VERIFY_SSL,
    PARAM_TIMEOUT,
    DEFAULT_BASE_URL,
    DEFAULT_TIMEOUT,
    DEFAULT_FETCH_STATUSES,
    ALL_KNOWN_SERVICES,
)

SCRIPT_NAME = "GetAlerts"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = SCRIPT_NAME

    api_key    = siemplify.extract_configuration_param(
        provider_name=INTEGRATION_NAME, param_name=PARAM_API_KEY, is_mandatory=True
    )
    base_url   = siemplify.extract_configuration_param(
        provider_name=INTEGRATION_NAME, param_name=PARAM_BASE_URL, default_value=DEFAULT_BASE_URL
    )
    verify_ssl = siemplify.extract_configuration_param(
        provider_name=INTEGRATION_NAME, param_name=PARAM_VERIFY_SSL,
        input_type=bool, default_value=True
    )
    timeout    = siemplify.extract_configuration_param(
        provider_name=INTEGRATION_NAME, param_name=PARAM_TIMEOUT,
        input_type=int, default_value=DEFAULT_TIMEOUT
    )

    services_raw  = siemplify.extract_action_param("Services",    is_mandatory=True)
    hours_back    = siemplify.extract_action_param("Hours Back",  input_type=int, default_value=24)
    max_results   = siemplify.extract_action_param("Max Results", input_type=int, default_value=50)
    statuses_raw  = siemplify.extract_action_param("Statuses",    default_value="")

    # Parse and validate services
    services = [s.strip() for s in services_raw.split(",") if s.strip()]
    unknown  = [s for s in services if s not in ALL_KNOWN_SERVICES]
    if unknown:
        siemplify.LOGGER.info(
            f"[{SCRIPT_NAME}] [WARN] Unknown service names (will attempt anyway): {unknown}"
        )

    statuses = (
        [s.strip().upper() for s in statuses_raw.split(",") if s.strip()]
        if statuses_raw.strip()
        else DEFAULT_FETCH_STATUSES
    )

    now = datetime.now(timezone.utc)
    gte = now - timedelta(hours=hours_back)

    try:
        manager = CybleManager(
            api_key=api_key, base_url=base_url, verify_ssl=verify_ssl, timeout=timeout
        )
        results = []
        for batch in manager.iter_alerts(
            services=services,
            gte=gte,
            lte=now,
            statuses=statuses,
            max_total=max_results,
        ):
            results.extend(batch)
            if len(results) >= max_results:
                results = results[:max_results]
                break

    except CybleAuthError as e:
        siemplify.end(f"Authentication failed: {e}", "false")
        return
    except CybleAPIError as e:
        siemplify.end(f"API error: {e}", "false")
        return

    now_iso = now.strftime("%Y-%m-%dT%H:%M:%S+00:00")
    mapped  = [CybleAlertMapper.cyble_to_secops_alert(r, now_iso) for r in results]

    output = json.dumps({
        "total_fetched": len(results),
        "services":      services,
        "window_hours":  hours_back,
        "alerts":        [
            {
                "alert_id": m["extensions"].get("AlertId"),
                "name":     m["name"],
                "severity": m["severity"],
                "service":  m["extensions"].get("Service"),
                "keyword":  m["extensions"].get("Keyword"),
                "status":   m["extensions"].get("Status", ""),
            }
            for m in mapped
        ],
    }, indent=2)

    siemplify.result.add_result_json(output)
    siemplify.end(
        f"Fetched {len(results)} alerts from services: {services}.",
        "true"
    )


if __name__ == "__main__":
    main()
