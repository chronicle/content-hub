from __future__ import annotations
import json
import socket
import sys
import paramiko
import errno

from soar_sdk.ScriptResult import (
    EXECUTION_STATE_COMPLETED,
    EXECUTION_STATE_INPROGRESS,
    EXECUTION_STATE_FAILED,
)
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyDataModel import InsightType
from soar_sdk.SiemplifyUtils import output_handler, convert_dict_to_json_result_dict
from TIPCommon import extract_configuration_param, extract_action_param, construct_csv
from ..core.VTFileOperationManager import FileOperationManager
from ..core.VirusTotal import (
    VirusTotalManager,
    VirusTotalInvalidAPIKeyManagerError,
    VirusTotalLimitManagerError,
)

SCRIPT_NAME = "VirusTotal - Upload files"
IDENTIFIER = "VirusTotal"
INSIGHT_CREATOR = "Siemplify_System"
INSIGHT_TITLE = "File {0} found as suspicious."
ENTITY_TYPE = "Entity Insight"
INSIGHT_SEVERITY_WARN = 1

THRESHOLD = 3


def start_operation(
    siemplify,
    manager,
    file_manager,
    file_paths,
    linux_server_address,
    linux_user,
    linux_password,
):
    """
    Main UploadAndScanFile action
    :param siemplify: SiemplifyAction object
    :param manager: VirusTotal object
    :param file_manager: FileOperationManager object
    :param file_paths: paths of files which will be checked
    :param linux_server_address: linux server address where files located
    :param linux_user: server user
    :param linux_password: server user password
    :return: {output message, not completed scans, execution state}
    """

    output_message = ""
    not_completed_scans = []
    failed_files = []
    limit_files = []

    for file_path in file_paths:
        # In case file is in remote linux send box
        try:
            if linux_server_address:
                # try:
                file_byte_array = file_manager.get_remote_unix_file_content(
                    linux_server_address, linux_user, linux_password, file_path
                )

                scan_id = manager.upload_file(file_path, file_byte_array)

            else:
                scan_id = manager.upload_file(file_path)

            siemplify.LOGGER.info(
                f"Successfully submitted {file_path}. Scan ID: {scan_id}"
            )

            not_completed_scans.append((file_path, scan_id))
            output_message += f"File was submitted successfully {file_path}\n"
        except paramiko.ssh_exception.AuthenticationException as e:
            err_msg = "Your login or password is incorrect"
            siemplify.LOGGER.error(err_msg)
            siemplify.LOGGER.exception(e)
            return err_msg, "false", EXECUTION_STATE_FAILED
        except (paramiko.ssh_exception.SSHException, socket.error) as e:
            err_msg = "Timeout error. Please check your server address"
            siemplify.LOGGER.error(err_msg)
            siemplify.LOGGER.exception(e)
            return err_msg, "false", EXECUTION_STATE_FAILED
        except IOError as e:
            if e.errno == errno.EACCES:
                err_msg = f"This file can not be accessible {file_path}"
            else:
                err_msg = f"File is not found on the server {file_path}"

            siemplify.LOGGER.info(f"Unable to submit {file_path}. Reason: {err_msg}")

            output_message += err_msg + "\n"
            siemplify.LOGGER.error(err_msg)
            failed_files.append(file_path)

        except VirusTotalInvalidAPIKeyManagerError as e:
            # Invalid key was passed - terminate action
            siemplify.LOGGER.error("Invalid API key was provided. Access is forbidden.")
            siemplify.LOGGER.exception(e)
            return (
                "Invalid API key was provided. Access is forbidden.",
                "false",
                EXECUTION_STATE_FAILED,
            )

        except VirusTotalLimitManagerError as e:
            siemplify.LOGGER.error(f"API limit reached for {file_path}.")
            siemplify.LOGGER.exception(e)
            limit_files.append(file_path)

        except Exception as e:
            err_msg = f"An error occurred on file {file_path}"
            siemplify.LOGGER.error(err_msg)
            siemplify.LOGGER.exception(e)
            failed_files.append(file_path)
            output_message += err_msg + "\n"

    msg = f"{len(not_completed_scans)} files were submitted successfully and {len(failed_files + limit_files)} files were not submitted"
    siemplify.LOGGER.info(msg)
    output_message += "\n" + msg + "\n"

    if not_completed_scans:
        return (
            output_message,
            json.dumps(([], not_completed_scans, failed_files, limit_files)),
            EXECUTION_STATE_INPROGRESS,
        )

    return output_message, "false", EXECUTION_STATE_FAILED


def query_operation_status(
    siemplify,
    manager,
    completed_scans,
    not_completed_scans,
    threshold,
    failed_files,
    limit_files,
):
    """
    Main UploadAndScanFile action
    :param siemplify: SiemplifyAction object
    :param manager: VirusTotal object
    :param completed_scans: list of completed scans
    :param not_completed_scans: list of non-completed scans
    :param threshold: action init param
    :param failed_files: list of failed scans
    :param limit_files: list of scans that failed due to API limitation
    :return: {output message, result, execution state}
    """
    json_results = {}
    result_value = "false"

    for file_path, scan_id in not_completed_scans:
        try:
            if not scan_id:
                continue

            siemplify.LOGGER.info(f"Fetching status of {file_path} (scan {scan_id})")
            report = manager.get_report_by_scan_id(scan_id)

            if not report:
                siemplify.LOGGER.info(f"File {file_path} is still queued for analysis.")
                continue

            json_results[file_path] = report.to_json()
            # Scan is complete
            siemplify.LOGGER.info(f"File {file_path} is ready.")
            completed_scans.append((file_path, scan_id, report.to_json()))

        except VirusTotalLimitManagerError:
            siemplify.LOGGER.info(
                f"API limit reached while checking if analysis of {file_path} has completed."
            )
            limit_files.append(file_path)

        except Exception as e:
            siemplify.LOGGER.exception(e)
            raise

    # Remove from not_completed_scans the scans that were completed
    not_completed_scans = [
        (file_path, scan_id)
        for file_path, scan_id in not_completed_scans
        if scan_id not in [scan[1] for scan in completed_scans]
    ]

    # Remove from not_completed_scans the scans that failed due to API limit
    not_completed_scans = [
        (file_path, scan_id)
        for file_path, scan_id in not_completed_scans
        if file_path not in limit_files
    ]

    if not_completed_scans:
        # Some scans were not completed yet
        siemplify.LOGGER.info("Not all scans have completed. Waiting.")
        output_massage = "Continuing... some of the requested items are still queued for analysis: {}".format(
            "\n".join(
                [not_completed_scan[0] for not_completed_scan in not_completed_scans]
            )
        )
        return (
            output_massage,
            json.dumps(
                (completed_scans, not_completed_scans, failed_files, limit_files)
            ),
            EXECUTION_STATE_INPROGRESS,
        )

    siemplify.LOGGER.info("All scans have completed. Collecting results.")

    for file_path, scan_id, report_json in completed_scans:
        try:
            siemplify.LOGGER.info(
                f"Collecting results for {file_path} (scan ID: {scan_id})"
            )
            # Scan detections_information
            report = manager.get_hash_report(report_json)
            data_table = construct_csv(report.build_engine_csv())
            siemplify.LOGGER.info(f"Adding CSV report for {file_path}")
            siemplify.result.add_data_table(f"{file_path} Report", data_table)

            # Add comments of resource
            comments = manager.get_comments(file_path)
            siemplify.LOGGER.info(f"Found {len(comments)} comments for {file_path}.")

            if comments:
                siemplify.LOGGER.info(f"Adding comments CSV table for {file_path}.")
                comments_table = construct_csv(
                    [comment.to_csv() for comment in comments]
                )
                siemplify.result.add_data_table(
                    f"Comments to {file_path}", comments_table
                )

            web_link = report.permalink
            siemplify.LOGGER.info(f"Adding report web link for {file_path}")
            siemplify.result.add_link(f"{file_path} Virus Total Web Link", web_link)

            # Check for risk
            if int(threshold) < report.positives:
                siemplify.LOGGER.info(
                    f"{file_path} was found risky by given threshold. Adding insight."
                )
                insight_message = (
                    "VirusTotal - {} marked as malicious by {} of {} engines - Threshold set to "
                    "- {} (if exceed threshold)".format(
                        file_path, report.positives, report.total, threshold
                    )
                )

                siemplify.create_case_insight(
                    INSIGHT_CREATOR,
                    INSIGHT_TITLE.format(file_path),
                    insight_message,
                    "",
                    INSIGHT_SEVERITY_WARN,
                    InsightType.Entity,
                )
                result_value = "true"

        except VirusTotalLimitManagerError:
            siemplify.LOGGER.error(f"API limit reached for {file_path}")
            limit_files.append(file_path)

    # Remove from completed the scans that failed due to API limit
    completed_scans = [
        (file_path, scan_id, report_json)
        for file_path, scan_id, report_json in completed_scans
        if file_path not in limit_files
    ]

    for file_path, scan_id, report_json in completed_scans:
        json_results[file_path] = report_json

    output_massage = ""
    if completed_scans:
        output_massage += (
            "The following files were uploaded to VirusTotal for scan: {}\n".format(
                "\n".join([completed_scan[0] for completed_scan in completed_scans])
            )
        )
    if failed_files:
        output_massage += "\nFailed to upload the following files: {}".format(
            "\n".join(failed_files)
        )

    if limit_files:
        output_massage += "\nThe following files were not uploaded properly due to reaching API request limitation: {}".format(
            "\n".join(limit_files)
        )

    # add json
    siemplify.LOGGER.info("Adding JSON results.")
    siemplify.result.add_result_json(convert_dict_to_json_result_dict(json_results))

    return output_massage, result_value, EXECUTION_STATE_COMPLETED


@output_handler
def main(is_first_run):
    siemplify = SiemplifyAction()
    siemplify.script_name = SCRIPT_NAME
    mode = "Main" if is_first_run else "QueryState"

    siemplify.LOGGER.info(f"----------------- {mode} - Param Init -----------------")

    # INIT INTEGRATION CONFIGURATION:
    api_key = extract_configuration_param(
        siemplify, provider_name=IDENTIFIER, param_name="Api Key", input_type=str
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=IDENTIFIER,
        param_name="Verify SSL",
        default_value=False,
        input_type=bool,
    )

    #  INIT ACTION PARAMETERS:
    file_paths = extract_action_param(
        siemplify,
        param_name="File Paths",
        is_mandatory=False,
        input_type=str,
        print_value=True,
    )
    linux_server_address = extract_action_param(
        siemplify,
        param_name="Linux Server Address",
        is_mandatory=False,
        input_type=str,
        print_value=False,
    )
    linux_user = extract_action_param(
        siemplify,
        param_name="Linux User",
        is_mandatory=False,
        input_type=str,
        print_value=False,
    )

    linux_password = extract_action_param(
        siemplify,
        param_name="Linux Password",
        is_mandatory=False,
        input_type=str,
        print_value=False,
    )

    threshold = extract_action_param(
        siemplify,
        param_name="Threshold",
        is_mandatory=False,
        input_type=int,
        print_value=True,
        default_value=3,
    )

    file_paths = (
        [file_path.strip() for file_path in file_paths.split(",")] if file_paths else []
    )

    output_message = ""
    siemplify.LOGGER.info(f"----------------- {mode} - Started -----------------")

    try:
        manager = VirusTotalManager(api_key, verify_ssl)
        file_manager = FileOperationManager()

        if is_first_run:

            output_message, result_value, status = start_operation(
                siemplify,
                manager,
                file_manager,
                file_paths,
                linux_server_address,
                linux_user,
                linux_password,
            )
        else:
            completed_scans, not_completed_scans, failed_files, limit_entities = (
                json.loads(siemplify.parameters["additional_data"])
            )
            query_output_message, result_value, status = query_operation_status(
                siemplify,
                manager,
                completed_scans,
                not_completed_scans,
                threshold,
                failed_files,
                limit_entities,
            )
            output_message += query_output_message

    except Exception as e:
        siemplify.LOGGER.error(f"General error performing action {SCRIPT_NAME}")
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = "false"
        output_message += "\n unknown failure"

    siemplify.LOGGER.info(f"----------------- {mode} - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  result_value: {result_value}\n  output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    is_first_run = len(sys.argv) < 3 or sys.argv[2] == "True"
    main(is_first_run)
