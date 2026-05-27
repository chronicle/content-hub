"""Get Threat Feed - Fetch IOCs from one or more SOCRadar Threat Feed collections."""
from __future__ import annotations
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from ..core.SOCRadarManager import SOCRadarManager

INTEGRATION_NAME = "SOCRadar"


@output_handler
def main() -> None:
    siemplify = SiemplifyAction()
    siemplify.script_name = "SOCRadar - Get Threat Feed"

    api_root = siemplify.extract_configuration_param(INTEGRATION_NAME, "API Root")
    api_key = siemplify.extract_configuration_param(INTEGRATION_NAME, "API Key")
    company_id = siemplify.extract_configuration_param(INTEGRATION_NAME, "Company ID")
    verify_ssl = siemplify.extract_configuration_param(INTEGRATION_NAME, "Verify SSL",
                                                       input_type=bool, default_value=True)

    uuids_raw = siemplify.extract_action_param("Collection UUIDs", is_mandatory=True)
    try:
        max_iocs = int(siemplify.extract_action_param("Max IOCs Per Feed", is_mandatory=False,
                                                       default_value="1000"))
    except (ValueError, TypeError):
        max_iocs = 1000
    ioc_type_filter = siemplify.extract_action_param("IOC Type Filter", is_mandatory=False,
                                                      default_value="")

    uuids = [u.strip() for u in uuids_raw.split(",") if u.strip()]
    if not uuids:
        siemplify.end("No valid UUIDs provided.", False)
        return

    try:
        manager = SOCRadarManager(api_root, api_key, company_id, verify_ssl)
        all_results = manager.get_multiple_ioc_feeds(uuids)

        output = []
        total_iocs = 0

        for uuid, feed_data in all_results.items():
            if isinstance(feed_data, dict) and "error" in feed_data:
                output.append({"collection_uuid": uuid, "error": feed_data["error"]})
                continue

            if not isinstance(feed_data, list):
                output.append({"collection_uuid": uuid, "error": "Unexpected response format"})
                continue

            # Apply IOC type filter if specified
            if ioc_type_filter:
                allowed_types = [t.strip().lower() for t in ioc_type_filter.split(",")]
                feed_data = [ioc for ioc in feed_data if isinstance(ioc, dict) and str(ioc.get("feed_type") or "").lower() in allowed_types]

            # Apply max limit
            feed_data = feed_data[:max_iocs]
            output.append({"collection_uuid": uuid, "ioc_count": len(feed_data), "iocs": feed_data})
            total_iocs += len(feed_data)

        siemplify.result.add_result_json(output)
        siemplify.end(f"Fetched {total_iocs} IOCs from {len(uuids)} feed(s).", True)
    except Exception as e:
        siemplify.end(f'Error executing action "Get Threat Feed". Reason: {e}', False)


if __name__ == "__main__":
    main()
