"""Enrich Indicator (STIX) - Get threat intelligence in STIX format from SOCRadar."""
from __future__ import annotations

from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

from ..core.SOCRadarManager import SOCRadarManager

INTEGRATION_NAME = "SOCRadar"


@output_handler
def main() -> None:
    siemplify = SiemplifyAction()
    siemplify.script_name = "SOCRadar - Enrich Indicator (STIX)"

    api_root = siemplify.extract_configuration_param(INTEGRATION_NAME, "API Root")
    api_key = siemplify.extract_configuration_param(INTEGRATION_NAME, "API Key")
    company_id = siemplify.extract_configuration_param(INTEGRATION_NAME, "Company ID")
    verify_ssl = siemplify.extract_configuration_param(INTEGRATION_NAME, "Verify SSL",
                                                       input_type=bool, default_value=True)
    ioc_api_key = siemplify.extract_configuration_param(INTEGRATION_NAME, "IOC Enrichment API Key",
                                                         default_value="")

    indicator = siemplify.extract_action_param("Indicator", is_mandatory=True)
    show_credits = siemplify.extract_action_param("Show Credit Details", is_mandatory=False,
                                                   default_value="false")

    if not ioc_api_key:
        siemplify.end("IOC Enrichment API Key is not configured. "
                      "Please set it in the integration configuration.", False)
        return

    try:
        manager = SOCRadarManager(api_root, api_key, company_id, verify_ssl)
        result = manager.enrich_indicator_stix(
            indicator,
            show_credit_details=(show_credits.lower() == "true"),
            ioc_api_key=ioc_api_key
        )
    
        siemplify.result.add_result_json(result)
    
        obj_count = len(result.get("objects", [])) if isinstance(result, dict) else 0
        summary = f"Enriched indicator (STIX): {indicator} | {obj_count} STIX objects returned"
    
        siemplify.end(summary, obj_count > 0)
    
    except Exception as e:
        siemplify.end(f'Error executing action "Enrich Indicator STIX". Reason: {e}', False)


if __name__ == "__main__":
    main()
