from __future__ import annotations

import json

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED, EXECUTION_STATE_INPROGRESS
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

from ..core.houdin import HoudinError, HoudinManager
from ..core.houdin_constants import INTEGRATION_NAME, SCAN_ARTIFACT_SCRIPT_NAME
from ..core.houdin_utils import load_state, parse_scanners, scan_link, verdict_line


@output_handler
def main() -> None:
    siemplify = SiemplifyAction()
    siemplify.script_name = SCAN_ARTIFACT_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    api_root = siemplify.extract_configuration_param(INTEGRATION_NAME, param_name="API Root")
    api_key = siemplify.extract_configuration_param(INTEGRATION_NAME, param_name="API Key")
    verify_ssl = siemplify.extract_configuration_param(
        INTEGRATION_NAME, param_name="Verify SSL", default_value=True, input_type=bool
    )
    artifact = siemplify.extract_action_param("Artifact", is_mandatory=True, print_value=True)
    scanners = parse_scanners(siemplify.extract_action_param("Scanners", print_value=True))
    force_rescan = siemplify.extract_action_param("Force Rescan", input_type=bool, default_value=False)
    state = load_state(siemplify.extract_action_param("additional_data"))

    try:
        houdin = HoudinManager(api_key, api_root, verify_ssl)

        if state is None:
            launch = houdin.launch_scan(artifact.strip(), scanners, force_rescan)
            siemplify.LOGGER.info(f"Scan {launch.scan_id} launched, status {launch.status!r}, cached {launch.cached}")
            state = {"scanID": launch.scan_id}
        document = houdin.wait_for_results([state["scanID"]]).get(state["scanID"])

        link = scan_link(state["scanID"])
        if document is None:
            siemplify.LOGGER.info(f"Scan {state['scanID']} is still in progress")
            siemplify.end(
                f"Houdin scan of {artifact} is in progress: {link}", json.dumps(state), EXECUTION_STATE_INPROGRESS
            )
            return

        siemplify.result.add_result_json(document)
        siemplify.result.add_link("Open in Houdin", link)
        output_message = f"Houdin scan of {artifact} completed. Threat score {verdict_line(document)}. {link}"
        siemplify.LOGGER.info(output_message)
        siemplify.end(output_message, "true", EXECUTION_STATE_COMPLETED)

    except HoudinError as error:
        siemplify.LOGGER.error(f"Houdin refused the scan of {artifact}: {error}")
        siemplify.end(f"Houdin could not scan {artifact}: {error}", "false", EXECUTION_STATE_FAILED)
    except Exception as error:
        siemplify.LOGGER.error(f"Scan Artifact failed: {error}")
        siemplify.LOGGER.exception(error)
        siemplify.end(f"Error executing action Scan Artifact. Reason: {error}", "false", EXECUTION_STATE_FAILED)


if __name__ == "__main__":
    main()
