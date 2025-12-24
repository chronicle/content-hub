import json

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

from ..core.houdin import HoudinManager

IDENTIFIER = "Houdin-io"
SCRIPT_NAME = "Houdin-io - Scan Artifact"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = SCRIPT_NAME

    api_key = siemplify.extract_configuration_param(siemplify, param_name="API Key")
    houdin = HoudinManager(api_key, verify_ssl=True)

    artifact = siemplify.extract_action_param("artifact")
    scanOn = siemplify.extract_action_param("scanOn")
    if isinstance(scanOn, str):
        scanOn = json.loads(scanOn or "[]")

    # Launch a scan on the provided artifact
    try:
        scan_id, status = houdin.launch_scan(artifact, scanOn)
    except Exception as e:
        siemplify.LOGGER.error(f"Error launching scan: {e}")
        siemplify.end(f"Error launching scan: {e}", False, EXECUTION_STATE_FAILED)
    siemplify.LOGGER.info(f"Scan launched with ID: {scan_id} and status: {status}")

    # Poll for the scan result
    try:
        result = houdin.poll_scan_result(scan_id)
        status = result.get("status", "Unknown")
        siemplify.LOGGER.info(f"Scan completed with status: {status}")
    except Exception as e:
        siemplify.LOGGER.error(f"Error polling scan result: {e}")
        siemplify.end(f"Error polling scan result: {e}", False, EXECUTION_STATE_FAILED)

    # Add the result to Siemplify
    siemplify.result.add_result_json(result)
    siemplify.result.add_json("HoudinResult", result)
    siemplify.end(f"Scan completed with status: {status}", True, EXECUTION_STATE_COMPLETED)


if __name__ == "__main__":
    main()
