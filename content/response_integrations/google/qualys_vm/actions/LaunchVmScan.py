from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler, unix_now
from soar_sdk.ScriptResult import (
    EXECUTION_STATE_COMPLETED,
    EXECUTION_STATE_FAILED,
    EXECUTION_STATE_INPROGRESS,
)
from soar_sdk.SiemplifyAction import SiemplifyAction
from TIPCommon import (
    extract_action_param,
    construct_csv,
    flat_dict_to_csv,
    dict_to_flat,
)
from ..core.manager_factory import create_qualys_manager_from_action
from ..core.constants import (
    INTEGRATION_NAME,
    LAUNCH_VM_SCAN_SCRIPT_NAME,
    SCAN_TEMPLATE,
    FINISH_STATE,
    ERROR_STATES,
)
from soar_sdk.SiemplifyDataModel import EntityTypes
from ..core.QualysVMExceptions import ScanErrorException
import sys
import uuid
import time
import base64
from ..core.QualysVMExceptions import QualysReportFailed

SUPPORTED_ENTITY_TYPES = [EntityTypes.ADDRESS]


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = LAUNCH_VM_SCAN_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    # Action parameters

    scan_title = extract_action_param(siemplify, param_name="Title", print_value=True)
    priority = extract_action_param(
        siemplify,
        param_name="Processing Priority",
        is_mandatory=True,
        default_value=0,
        print_value=True,
    )
    option_title = extract_action_param(
        siemplify, param_name="Scan Profile", is_mandatory=True, print_value=True
    )
    iscanner_name = extract_action_param(
        siemplify,
        param_name="Scanner Appliance",
        default_value="External",
        print_value=True,
    )
    ip_network_id = extract_action_param(
        siemplify, param_name="Network", default_value=0, print_value=True
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    status = EXECUTION_STATE_INPROGRESS
    ips = []
    suitable_entities = [
        entity
        for entity in siemplify.target_entities
        if entity.entity_type in SUPPORTED_ENTITY_TYPES
    ]
    # If scan name is not given - generate one
    scan_title = scan_title if scan_title else f"Scan {str(uuid.uuid4().hex[:10])}"

    try:
        qualys_manager = create_qualys_manager_from_action(siemplify)

        for entity in suitable_entities:
            siemplify.LOGGER.info(f"\nStarted processing entity: {entity.identifier}")

            try:
                qualys_manager.add_ip(entity.identifier)
                ips.append(entity.identifier)
            except Exception as e:
                # An error occurred - skip entity and continue
                siemplify.LOGGER.error(
                    f"An error occurred on entity: {entity.identifier}.\n{str(e)}."
                )
                siemplify.LOGGER.exception(e)

            siemplify.LOGGER.info(f"Finished processing entity {entity.identifier}\n")

        scan_ref = qualys_manager.launch_vm_scan(
            scan_title=scan_title,
            priority=priority,
            option_title=option_title,
            ip=",".join(ips),
            iscanner_name=iscanner_name,
            ip_network_id=ip_network_id,
        )

        entities_to_update = []

        for entity in suitable_entities:
            entity.additional_properties.update({"qualys_last_scan_id": scan_ref})
            entity.is_enriched = True
            entities_to_update.append(entity)

        siemplify.update_entities(entities_to_update)
        output_message = f"VM scan was initialized. Scan reference: {scan_ref}."
    except Exception as e:
        siemplify.LOGGER.error(
            f"General error performing action {LAUNCH_VM_SCAN_SCRIPT_NAME}"
        )
        siemplify.LOGGER.exception(e)
        scan_ref = False
        status = EXECUTION_STATE_FAILED
        output_message = (
            f'Error executing action "{LAUNCH_VM_SCAN_SCRIPT_NAME}". Reason: {e}'
        )

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result: {scan_ref}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")

    siemplify.end(output_message, scan_ref, status)


def wait_for_results():
    siemplify = SiemplifyAction()
    action_start_time = unix_now()
    siemplify.script_name = LAUNCH_VM_SCAN_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    status = EXECUTION_STATE_INPROGRESS
    json_results = {}

    try:
        qualys_manager = create_qualys_manager_from_action(siemplify)
        scan_id = siemplify.parameters["additional_data"]

        if qualys_manager.is_scan_in_error_state(scan_id):
            raise ScanErrorException

        if qualys_manager.is_scan_completed(scan_id):
            results = qualys_manager.get_vm_scan_results(scan_id)

            report_id = qualys_manager.launch_scan_report(
                report_title=f"Scan {scan_id} Report",
                template_id=qualys_manager.get_template_id_by_name(SCAN_TEMPLATE),
                output_format="pdf",
                report_refs=[scan_id],
            )

        timeout_counter = 0
        while True:
            timeout_counter = timeout_counter + 1

            if timeout_counter > 30:  # 150seconds is the timeout limit
                raise Exception(
                    f'Timeout is approaching. Action will gracefully exit. Please use action: "Download Vm Scan Results" to fetch results for scan with ID: {scan_id}.'
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
                time.sleep(5)
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

            if json_results:
                siemplify.result.add_result_json(json_results)

            output_message = "The following hosts were submitted and analyzed in Qualys VM: {}".format(
                "\n".join(
                    [
                        entity.identifier
                        for entity in siemplify.target_entities
                        if entity.entity_type == EntityTypes.ADDRESS
                    ]
                )
            )
            result = scan_id
            status = EXECUTION_STATE_COMPLETED
        else:
            output_message = f"Results were not fetched. Scan {scan_id} may not be completed, trying again."
            result = scan_id
            status = EXECUTION_STATE_INPROGRESS
    except ScanErrorException:
        output_message = (
            "An error occurred in scan. Scan was canceled, paused or completed with an error. "
            "Unable to get results."
        )
        result = scan_id
        status = EXECUTION_STATE_FAILED
    except Exception as e:
        siemplify.LOGGER.error(
            f"General error performing action {LAUNCH_VM_SCAN_SCRIPT_NAME}"
        )
        siemplify.LOGGER.exception(e)
        result = False
        status = EXECUTION_STATE_FAILED
        output_message = (
            f'Error executing action "{LAUNCH_VM_SCAN_SCRIPT_NAME}". Reason: {e}'
        )

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result: {result}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, result, status)


if __name__ == "__main__":
    if len(sys.argv) < 3 or sys.argv[2] == "True":
        main()
    else:
        wait_for_results()
