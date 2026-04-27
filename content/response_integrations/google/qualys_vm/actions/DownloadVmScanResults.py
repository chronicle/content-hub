from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler, unix_now, convert_unixtime_to_datetime
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from TIPCommon import (
    extract_action_param,
    flat_dict_to_csv,
    construct_csv,
    dict_to_flat,
)
from ..core.manager_factory import create_qualys_manager_from_action
from ..core.constants import (
    INTEGRATION_NAME,
    DOWNLOAD_VM_SCAN_RESULTS_SCRIPT_NAME,
    SCAN_TEMPLATE,
    FINISH_STATE,
    ERROR_STATES,
)
import base64
import time
import json
from ..core.QualysVMExceptions import QualysReportFailed


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = DOWNLOAD_VM_SCAN_RESULTS_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    # Action parameters
    scan_id = extract_action_param(
        siemplify, param_name="Scan ID", is_mandatory=True, print_value=True
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    result = True
    status = EXECUTION_STATE_COMPLETED
    json_results = {}

    try:
        qualys_manager = create_qualys_manager_from_action(siemplify)
        results = qualys_manager.get_vm_scan_results(scan_id)

        report_id = qualys_manager.launch_scan_report(
            report_title=f"Scan {scan_id} Report",
            template_id=qualys_manager.get_template_id_by_name(SCAN_TEMPLATE),
            output_format="pdf",
            report_refs=[scan_id],
        )

        while True:
            if unix_now() >= siemplify.execution_deadline_unix_time_ms:
                siemplify.LOGGER.error(
                    f"Timed out. execution deadline ({convert_unixtime_to_datetime(siemplify.execution_deadline_unix_time_ms)}) has passed"
                )
            try:
                # Try to fetch the report
                report = qualys_manager.get_report(report_id)

                if report.get("STATUS", {}).get("STATE") == FINISH_STATE:
                    json_results = report
                    break

                if report.get("STATUS", {}).get("STATE") in ERROR_STATES:
                    raise QualysReportFailed(
                        f"Report {report_id} ended with error. Couldn't download the report."
                    )

            except QualysReportFailed as e:
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

        if results:
            results_summary = results[1]
            actual_results = results[2:]
            siemplify.result.add_data_table(
                "Report Summary", flat_dict_to_csv(dict_to_flat(results_summary))
            )
            siemplify.result.add_data_table(
                "Scan Results", construct_csv(actual_results)
            )
            json_results = json.dumps(results)

        # add json result
        if json_results:
            siemplify.result.add_result_json(json_results)

        output_message = f"Scan results fetched for scan: {scan_id}"

    except Exception as e:
        siemplify.LOGGER.error(
            f"General error performing action {DOWNLOAD_VM_SCAN_RESULTS_SCRIPT_NAME}"
        )
        siemplify.LOGGER.exception(e)
        result = False
        status = EXECUTION_STATE_FAILED
        output_message = f'Error executing action "{DOWNLOAD_VM_SCAN_RESULTS_SCRIPT_NAME}". Reason: {e}'

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result: {result}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")

    siemplify.end(output_message, result, status)


if __name__ == "__main__":
    main()
