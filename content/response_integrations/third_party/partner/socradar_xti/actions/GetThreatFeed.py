"""Get Threat Feed - Fetch IOCs from one or more SOCRadar Threat Feed collections."""
import json
from SiemplifyAction import SiemplifyAction
from SiemplifyUtils import output_handler
from SOCRadarManager import SOCRadarManager

INTEGRATION_NAME = "SOCRadar"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = "SOCRadar - Get Threat Feed"

    api_root = siemplify.extract_configuration_param(INTEGRATION_NAME, "API Root")
    api_key = siemplify.extract_configuration_param(INTEGRATION_NAME, "API Key")
    company_id = siemplify.extract_configuration_param(INTEGRATION_NAME, "Company ID")
    verify_ssl = siemplify.extract_configuration_param(INTEGRATION_NAME, "Verify SSL",
                                                       input_type=bool, default_value=True)

    uuids_raw = siemplify.extract_action_param("Collection UUIDs", is_mandatory=True)
    max_iocs = int(siemplify.extract_action_param("Max IOCs Per Feed", is_mandatory=False,
                                                   default_value="1000"))
    ioc_type_filter = siemplify.extract_action_param("IOC Type Filter", is_mandatory=False,
                                                      default_value="")

    uuids = [u.strip() for u in uuids_raw.split(",") if u.strip()]
    if not uuids:
        siemplify.end("No valid UUIDs provided.", False)
        return

    manager = SOCRadarManager(api_root, api_key, company_id, verify_ssl)
    all_results = manager.get_multiple_ioc_feeds(uuids)

    output = {}
    total_iocs = 0

    for uuid, feed_data in all_results.items():
        if isinstance(feed_data, dict) and "error" in feed_data:
            output[uuid] = feed_data
            continue

        if not isinstance(feed_data, list):
            output[uuid] = {"error": "Unexpected response format"}
            continue

        # Apply IOC type filter if specified
        if ioc_type_filter:
            allowed_types = [t.strip().lower() for t in ioc_type_filter.split(",")]
            feed_data = [ioc for ioc in feed_data if ioc.get("feed_type", "").lower() in allowed_types]

        # Apply max limit
        feed_data = feed_data[:max_iocs]
        output[uuid] = {"ioc_count": len(feed_data), "iocs": feed_data}
        total_iocs += len(feed_data)

    siemplify.result.add_result_json(output)
    siemplify.end(f"Fetched {total_iocs} IOCs from {len(uuids)} feed(s).", total_iocs > 0)


if __name__ == "__main__":
    main()
