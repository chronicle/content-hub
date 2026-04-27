from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from TIPCommon import extract_action_param
from ..core.manager_factory import create_qualys_manager_from_action
from ..core.QualysVMExceptions import QualysVMManagerError
from ..core.constants import (
    INTEGRATION_NAME,
    FETCH_REPORT_SCRIPT_NAME,
    FINISH_STATE,
    ERROR_STATES,
)
import base64
import time


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = FETCH_REPORT_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    # Action parameters
    report_id = extract_action_param(
        siemplify, param_name="Report ID", is_mandatory=True, print_value=True
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    result = True
    status = EXECUTION_STATE_COMPLETED
    json_results = {}

    try:
        qualys_manager = create_qualys_manager_from_action(siemplify)

        while True:
            try:
                # Try to fetch the report
                report = qualys_manager.get_report(report_id)

                if report.get("STATUS", {}).get("STATE") == FINISH_STATE:
                    json_results = report
                    break

                if report.get("STATUS", {}).get("STATE") in ERROR_STATES:
                    raise QualysVMManagerError(
                        f"Report {report_id} ended with error. Couldn't download the report."
                    )

            except QualysVMManagerError as e:
                raise

            except Exception:
                # Report was not yet initiated and created in the DB - try again
                time.sleep(1)
                continue

        report_data = qualys_manager.fetch_report(report_id=report_id)

        siemplify.result.add_attachment(
            title=f"Report {report_id}",
            filename=report_data["name"],
            file_contents=base64.b64encode(report_data["content"]).decode(),
        )

        if json_results:
            siemplify.result.add_result_json(json_results)

        output_message = f"Report {report_id} was downloaded as attachment."

    except Exception as e:
        siemplify.LOGGER.error(
            f"General error performing action {FETCH_REPORT_SCRIPT_NAME}"
        )
        siemplify.LOGGER.exception(e)
        result = False
        status = EXECUTION_STATE_FAILED
        output_message = (
            f'Error executing action "{FETCH_REPORT_SCRIPT_NAME}". Reason: {e}'
        )

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result: {result}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")

    siemplify.end(output_message, result, status)


if __name__ == "__main__":
    main()
