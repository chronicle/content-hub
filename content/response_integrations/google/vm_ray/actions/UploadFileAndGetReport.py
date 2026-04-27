from __future__ import annotations
import sys
import os
import json
import base64
from soar_sdk.SiemplifyUtils import output_handler, unix_now
from soar_sdk.SiemplifyAction import SiemplifyAction
from TIPCommon import (
    extract_configuration_param,
    extract_action_param,
    construct_csv,
    dict_to_flat,
)
from soar_sdk.ScriptResult import (
    EXECUTION_STATE_COMPLETED,
    EXECUTION_STATE_INPROGRESS,
    EXECUTION_STATE_FAILED,
)
from ..core.VMRayClientManager import VMRayClient
from ..core.constants import INTEGRATION_NAME, UPLOAD_FILE_SCRIPT_NAME
from ..core.UtilsManager import (
    convert_comma_separated_to_list,
    is_approaching_timeout,
    get_system_versions,
)
from ..core.VMRayParser import VMRayParser


def get_not_accessible_files(files):
    not_accessible_files = []
    for file in files:
        if not os.path.exists(file):
            not_accessible_files.append(file)
        elif not os.access(file, os.R_OK):
            not_accessible_files.append(file)

    return not_accessible_files


def process_results(sample_analyses, filename, vmray_manager, siemplify):
    siemplify.result.add_link(
        f"Report Link: {filename}", sample_analyses.sample_webif_url
    )

    # Get Sample IOCS
    iocs_object = vmray_manager.get_sample_iocs(sample_analyses.sample_id)

    if iocs_object:
        flat_iocs_files = list(
            map(
                lambda ioc_file: dict_to_flat(ioc_file.to_dict()), iocs_object.ioc_files
            )
        )
        if flat_iocs_files:
            siemplify.result.add_data_table(
                f"IOCS - Files: {filename}", construct_csv(flat_iocs_files)
            )

        flat_iocs_ips = list(
            map(lambda ioc_ip: dict_to_flat(ioc_ip.to_dict()), iocs_object.ioc_ips)
        )
        if flat_iocs_ips:
            siemplify.result.add_data_table(
                f"IOCS - IPs: {filename}", construct_csv(flat_iocs_ips)
            )

        flat_iocs_urls = list(
            map(lambda ioc_url: dict_to_flat(ioc_url.to_dict()), iocs_object.ioc_urls)
        )
        if flat_iocs_urls:
            siemplify.result.add_data_table(
                f"IOCS - URLs: {filename}", construct_csv(flat_iocs_urls)
            )

        flat_iocs_registries = list(
            map(
                lambda ioc_registry: dict_to_flat(ioc_registry.to_dict()),
                iocs_object.ioc_registries,
            )
        )
        if flat_iocs_registries:
            siemplify.result.add_data_table(
                f"IOCS - Registry Keys: {filename}", construct_csv(flat_iocs_registries)
            )

        flat_ioc_domains = list(
            map(
                lambda ioc_domain: dict_to_flat(ioc_domain.to_dict()),
                iocs_object.ioc_domains,
            )
        )
        if flat_ioc_domains:
            siemplify.result.add_data_table(
                f"IOCS - Domains: {filename}", construct_csv(flat_ioc_domains)
            )

        flat_ioc_mutexes = list(
            map(
                lambda ioc_mutex: dict_to_flat(ioc_mutex.to_dict()),
                iocs_object.ioc_mutexes,
            )
        )
        if flat_ioc_mutexes:
            siemplify.result.add_data_table(
                f"IOCS - Mutexes: {filename}", construct_csv(flat_ioc_mutexes)
            )

    # Get Sample Threat Indicators
    threat_indicators = vmray_manager.get_sample_threat_indicators(
        sample_analyses.sample_id
    )

    if threat_indicators:
        flat_threat_indicators = list(
            map(
                lambda threat_indicator: dict_to_flat(threat_indicator.to_json()),
                threat_indicators,
            )
        )
        siemplify.result.add_entity_table(
            f"Threat Indicators: {filename}", construct_csv(flat_threat_indicators)
        )

    # Get last analysis id and download its reports
    analysis_id = vmray_manager.get_last_analysis_id_by_sample(
        sample_analyses.sample_id
    )

    if analysis_id:
        analysis_json = vmray_manager.get_json_analysis_archive(analysis_id)
        analysis_zip = vmray_manager.get_zip_analysis_archive(analysis_id)

        siemplify.result.add_attachment(
            f"JSON Report {filename}",
            f"analysis_{analysis_id}.json",
            base64.b64encode(analysis_json).decode(),
        )

        siemplify.result.add_attachment(
            f"Report ZIP: {filename}",
            f"analysis_{analysis_id}.zip",
            base64.b64encode(analysis_zip).decode(),
        )


def start_operation(siemplify, vmray_manager):
    # action parameters
    sample_files = convert_comma_separated_to_list(
        extract_action_param(
            siemplify,
            param_name="Sample File Path",
            is_mandatory=True,
            print_value=True,
        )
    )
    tag_names = extract_action_param(
        siemplify, param_name="Tag Names", print_value=True
    )
    comment = extract_action_param(siemplify, param_name="Comment", print_value=True)

    status = EXECUTION_STATE_INPROGRESS
    result_value = {
        "in_progress": {},
        "completed": {},
        "failed": [],
        "timestamp": unix_now(),
    }
    successful_files, failed_files = [], []

    not_accessible_files = get_not_accessible_files(sample_files)

    if not_accessible_files:
        raise Exception(
            f"the following files were not accessible: {', '.join(not_accessible_files)}"
        )

    for sample_file in sample_files:
        try:
            sample_res_obj = vmray_manager.submit_sample_file(
                sample_file, tag_names, comment
            )
            siemplify.LOGGER.info(f"Got submission results for file: {sample_file}")
            if not sample_res_obj:
                raise

            if sample_res_obj.samples:
                siemplify.LOGGER.info(f"File uploaded successfully: {sample_file}")
                result_value["in_progress"][sample_file] = sample_res_obj.to_json()
            else:
                siemplify.LOGGER.info(f"File uploaded successfully: {sample_file}")
                result_value["completed"][sample_file] = sample_res_obj.to_json()

            successful_files.append(sample_file)

        except Exception as err:
            failed_files.append(sample_file)
            siemplify.LOGGER.error(f"An error occurred on file {sample_file}")
            siemplify.LOGGER.exception(err)

    if successful_files:
        result_value = json.dumps(result_value)
        output_message = f"Successfully uploaded files: {', '.join(successful_files)}."
    else:
        output_message = "File submission failed."
        result_value = False
        status = EXECUTION_STATE_COMPLETED

    return output_message, result_value, status


def query_operation_status(siemplify, vmray_manager, result_data):
    completed_files = {}

    for file_name, sample_res_raw_data in result_data["in_progress"].items():
        sample_res_obj = VMRayParser().build_sample_res_object(sample_res_raw_data)
        if is_approaching_timeout(
            result_data["timestamp"], siemplify.execution_deadline_unix_time_ms
        ):
            raise Exception(
                f"action ran into a timeout. Pending files: {', '.join(result_data['in_progress'].keys())}."
                f" Please increase the timeout in the IDE. Note: action will submit all of the provided "
                f"files again for the analysis."
            )

        sample_id = None
        submission_id = None
        if sample_res_obj.samples:
            sample_id = sample_res_obj.sample_id

        if sample_res_obj.submissions:
            submission_id = sample_res_obj.submissions[0].submission_id

        siemplify.LOGGER.info(f"Checking state for file: {file_name}")
        try:
            if vmray_manager.is_submission_finished(submission_id):
                sample_analyses = vmray_manager.get_sample_by_id(sample_id)
                completed_files[file_name] = sample_analyses.to_json()

        except Exception as err:
            result_data["failed"].append(file_name)
            siemplify.LOGGER.error(f"An error occurred on file {file_name}")
            siemplify.LOGGER.exception(err)

    for key in completed_files.keys():
        result_data["in_progress"].pop(key)
    # Update completed files with completed_files dict including json_result
    result_data["completed"].update(completed_files)

    if result_data["in_progress"]:
        status = EXECUTION_STATE_INPROGRESS
        result_value = json.dumps(result_data)
        output_message = f"Waiting for the results of: {', '.join(result_data['in_progress'].keys())}"
    else:
        output_message, result_value, status = finish_operation(
            siemplify=siemplify, vmray_manager=vmray_manager, result_data=result_data
        )

    return output_message, result_value, status


def finish_operation(siemplify, vmray_manager, result_data):
    failed_files = result_data["failed"]
    successful_files, csv_output = [], []
    output_message = ""
    result_value = True
    status = EXECUTION_STATE_COMPLETED

    for file_name, sample_analyses in result_data["completed"].items():
        try:
            sample_analyses = VMRayParser().build_sample_analyses_object(
                sample_analyses
            )
            process_results(sample_analyses, file_name, vmray_manager, siemplify)
            successful_files.append(file_name)
            csv_output.append(dict_to_flat(sample_analyses.to_json()))
        except Exception as e:
            failed_files.append(file_name)
            siemplify.LOGGER.error(f"An error occurred on file {file_name}")
            siemplify.LOGGER.exception(e)

    if successful_files:
        siemplify.result.add_data_table("Results", construct_csv(csv_output))
        output_message += f"Successfully submitted the following files to VMRay: {', '.join(successful_files)}\n"

        if failed_files:
            output_message += f"Action wasn't able to submit the following files to VMRay: {', '.join(failed_files)}\n"

    else:
        output_message = f"No files were submitted to VMRay."
        result_value = False

    return output_message, result_value, status


@output_handler
def main(is_first_run):
    siemplify = SiemplifyAction()
    siemplify.script_name = UPLOAD_FILE_SCRIPT_NAME
    mode = "Main" if is_first_run else "Get Report"
    siemplify.LOGGER.info(f"----------------- {mode} - Param Init -----------------")

    # integration configuration
    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Api Root",
        print_value=True,
    )
    api_key = extract_configuration_param(
        siemplify, provider_name=INTEGRATION_NAME, param_name="Api Key"
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        is_mandatory=True,
        input_type=bool,
        print_value=True,
    )

    siemplify.LOGGER.info(f"----------------- {mode} - Started -----------------")

    output_message = ""
    result_value = False
    status = EXECUTION_STATE_INPROGRESS

    try:
        vmray_manager = VMRayClient(
            api_root, api_key, verify_ssl, **get_system_versions(siemplify)
        )

        if is_first_run:
            output_message, result_value, status = start_operation(
                siemplify, vmray_manager=vmray_manager
            )
        if status == EXECUTION_STATE_INPROGRESS:
            result_data = (
                result_value
                if result_value
                else extract_action_param(
                    siemplify, param_name="additional_data", default_value="{}"
                )
            )
            output_message, result_value, status = query_operation_status(
                siemplify=siemplify,
                vmray_manager=vmray_manager,
                result_data=json.loads(result_data),
            )
    except Exception as e:
        output_message = (
            f"Error executing action {UPLOAD_FILE_SCRIPT_NAME}. Reason: {e}"
        )
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = False

    siemplify.LOGGER.info(f"----------------- {mode} - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  is_success: {result_value}\n  output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    is_first_run = len(sys.argv) < 3 or sys.argv[2] == "True"
    main(is_first_run)
