import ipaddress
import json

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyUtils import output_handler

from ..core.houdin import HoudinManager

IDENTIFIER = "Houdin-io"
SCRIPT_NAME = "Houdin-io - Enrich Entities"


def isIPExternal(addr):
    try:
        return ipaddress.ip_address(addr).is_global
    except Exception:
        return False


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = SCRIPT_NAME

    api_key = siemplify.extract_configuration_param(siemplify, param_name="API Key")
    houdin = HoudinManager(api_key, verify_ssl=True)

    scanOn = siemplify.extract_action_param("scanOn")
    if isinstance(scanOn, str):
        scanOn = json.loads(scanOn or "[]")

    successful_entities = []
    json_results = []
    output_message = ""

    scanIDToEntityMap = {}
    try:
        for entity in siemplify.target_entities:
            if (
                entity.entity_type == EntityTypes.URL
                or (entity.entity_type == EntityTypes.ADDRESS and isIPExternal(entity.identifier))
                or entity.entity_type == EntityTypes.DOMAIN
                or entity.entity_type == EntityTypes.FILEHASH
                or entity.entity_type == "DestinationURL"
            ):
                entity_to_scan = entity.identifier
                siemplify.LOGGER.info(f"Processing compatible entity {entity_to_scan}")
                scan_id, status = houdin.launch_scan(entity_to_scan, scanOn)
                scanIDToEntityMap[scan_id] = entity
    except Exception as e:
        siemplify.LOGGER.error(f"Error launching scan: {e}")
        siemplify.end(f"Error launching scan: {e}", False, EXECUTION_STATE_FAILED)

    # We launch scans in bulk and retrieve all results later to optimize polling time a bit
    scanIDList = list(scanIDToEntityMap.keys())
    try:
        for scanID in scanIDList:
            res = houdin.poll_scan_result(scanID)
            mesmerRes = (
                res.get("scanResults", {})
                .get("mesmer", {})
                .get("result", {})
                .get("globalScore", "")
            )
            if mesmerRes != "" and mesmerRes:
                mesmerRes += "/10"
            mesmerSummary = (
                res.get("scanResults", {}).get("mesmer", {}).get("result", {}).get("summary", "")
            )
            scannedOn = ", ".join(res.get("scanOn", []))
            for e in siemplify.target_entities:
                if e.identifier == scanIDToEntityMap[scanID].identifier:
                    e.additional_properties.update({
                        "Houdin-io_Threat_Score": mesmerRes,
                        "Houdin-io_AI_Analysis": mesmerSummary,
                        "Houdin-io_Analysis_sources": scannedOn,
                    })
                    successful_entities.append(e)
                    json_results.append({"Entity": e, "EntityResult": res})
        if successful_entities:
            output_message += "\n Successfully processed entities:\n {}".format(
                "\n".join([x.identifier for x in successful_entities])
            )
            siemplify.update_entities(successful_entities)
        else:
            output_message += "\n No entities where processed.\n "
            output_message += (
                "Compatible types are: Public IPv4/IPv6, URL, Domain, MD5, SHA1, SHA256"
            )
    except Exception as e:
        siemplify.LOGGER.error(f"Error polling scan result: {e}")
        siemplify.end(f"Error polling scan result: {e}", False, EXECUTION_STATE_FAILED)

    result_value = len(successful_entities)
    siemplify.result.add_result_json(json_results)
    siemplify.end(output_message, result_value, EXECUTION_STATE_COMPLETED)


if __name__ == "__main__":
    main()
