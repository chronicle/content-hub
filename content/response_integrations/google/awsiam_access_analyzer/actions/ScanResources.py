from __future__ import annotations
import json
import sys

from TIPCommon import extract_configuration_param, extract_action_param

from ..core.AWSIAMAnalyzerManager import AWSIAMAnalyzerManager
from soar_sdk.ScriptResult import (
    EXECUTION_STATE_COMPLETED,
    EXECUTION_STATE_FAILED,
    EXECUTION_STATE_INPROGRESS,
)
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler, unix_now
from ..core.consts import INTEGRATION_NAME, MAX_RETRIES
from ..core.exceptions import AWSIAMNotFoundException, AWSIAMAnalyzerNotFoundException
from ..core.utils import load_csv_to_list

SCRIPT_NAME = "Scan Resources"


def submit_resources(
    siemplify, manager, analyzer_arn, resource_arns, action_starting_time
):
    """
    Submit resources for a scan
    :param siemplify: {SiemplifyAction} SiemplifyAction object
    :param manager: {AWSIAMAnalyzerManager} manager object
    :param analyzer_arn: {str} the arn of an analyzer
    :param resource_arns: {list} list of arn resources
    :param action_starting_time: {int} unix time in ms
    :return: (output message, result_value, execution state)
    """
    status = EXECUTION_STATE_INPROGRESS
    json_result = {
        "action_starting_time": action_starting_time,
        "unprocessed_resources": [],  # list of resources that were initially successfully submitted for a scan
        "failed_resources": [],  # resources that failed to be submitted for a scan
        "processed_resources": [],  # processed resources
        "resources": [],  # list of resources analyzed details
        "retries": 0,
    }

    output_message = ""

    try:
        for resource in resource_arns:  # start resource scan
            try:
                siemplify.LOGGER.info(f"Starting scanning resource arn {resource}")
                manager.start_resource_scan(
                    analyzer_arn=analyzer_arn, resource_arn=resource
                )
                siemplify.LOGGER.info(
                    f"Successfully submitted resource arn {resource} for a scan of the "
                    "policies applied to the resource"
                )
                json_result["unprocessed_resources"].append(resource)
            except Exception as e:
                json_result["failed_resources"].append(resource)
                siemplify.LOGGER.error(
                    f"An error occurred submitting a scan for resource {resource}"
                )
                siemplify.LOGGER.exception(e)

        if json_result["unprocessed_resources"]:
            siemplify.LOGGER.info(
                "Waiting for the following resources to be scanned using {}:\n    "
                "{}".format(
                    INTEGRATION_NAME, "\n  ".join(json_result["unprocessed_resources"])
                )
            )
            output_message += (
                "Waiting for the following resources to be scanned using "
                "{}:\n    {}").format(
                INTEGRATION_NAME, "\n  ".join(json_result["unprocessed_resources"])
            )
            result_value = json.dumps(json_result)
        else:  # None of the resources were successfully submitted for a scan
            status = EXECUTION_STATE_COMPLETED
            output_message += "No resources were scanned."
            result_value = "false"
            if json_result["failed_resources"]:
                output_message += (
                    "\n\nAction was not able to scan the following resources using {}:"
                    "\n   {}").format(
                    INTEGRATION_NAME, "\n   ".join(json_result["failed_resources"])
                )

    except Exception as error:  # action failed, stops playbook
        siemplify.LOGGER.error(
            f"Error executing action '{SCRIPT_NAME}'. Reason: {error}"
        )
        siemplify.LOGGER.exception(error)
        status = EXECUTION_STATE_FAILED
        result_value = "false"
        output_message = f"Error executing action '{SCRIPT_NAME}'. Reason: {error}"

    return output_message, result_value, status


def get_analyzed_resources(siemplify, manager, analyzer_arn):
    """
    Part of the action that periodically fetches analyzed information from processed resources
    :param siemplify: {SiemplifyAction} SiemplifyAction object
    :param manager: {AWSIAMAnalyzerManager} manager object
    :param analyzer_arn: {str} the arn of an analyzer
    :return: (output message, json_result, execution status)
    """
    # result value from previous runs
    previous_result_value = json.loads(
        siemplify.extract_action_param("additional_data")
    )
    unprocessed_resources = previous_result_value["unprocessed_resources"]
    action_starting_time = previous_result_value["action_starting_time"]

    new_processed_resources = []  # processed resources for this action iteration
    new_unprocessed_resources = []  # unprocessed_resources for this action iteration

    output_message = ""

    json_result = {  # action's async result value represented as dictionary
        "action_starting_time": action_starting_time,
        "unprocessed_resources": [],  # list of resources that were initially successfully submitted for a scan
        "failed_resources": previous_result_value["failed_resources"],
        # resource ARNs that were already processed
        "processed_resources": previous_result_value["processed_resources"],
        # list of already processed resources and their analyzed information details
        "resources": previous_result_value["resources"],
        # number of retries
        "retries": previous_result_value["retries"],
    }

    for resource in unprocessed_resources:
        try:
            resource_obj = manager.get_analyzed_resource(
                analyzer_arn=analyzer_arn, resource_arn=resource
            )
            siemplify.LOGGER.info(
                f"Successfully retrieved information for resource {resource}"
            )
            siemplify.LOGGER.info(
                f"Resource {resource} was last analyzed at "
                f"{resource_obj.analyzedAt_timestamp}"
            )
            # if the analyzedAt field is greater or equals to action's starting time, resource finished analyzing
            if resource_obj.analyzedAt_timestamp >= action_starting_time:
                siemplify.LOGGER.info(f"Resource {resource} finished scanning")
                new_processed_resources.append(resource)
                json_result["resources"].append(
                    resource_obj.as_json()
                )  # save resource analyzed details
            else:
                siemplify.LOGGER.info(f"Resource {resource} didn't finish scanning")
                new_unprocessed_resources.append(resource)

        except (
            AWSIAMNotFoundException
        ) as e:  # if resource is not found continue waiting for scan result
            siemplify.LOGGER.info(f"Resource {resource} was not found")
            new_unprocessed_resources.append(resource)

        except Exception as error:
            json_result["failed_resources"].append(resource)
            siemplify.LOGGER.error(
                f"Failed to retrieve information about resource {resource} that was "
                "submitted for a scan"
            )
            siemplify.LOGGER.exception(error)

    # if action has no new unprocessed resources, or reached max retries -  end action execution
    if (not new_unprocessed_resources) or json_result["retries"] >= MAX_RETRIES:
        status = EXECUTION_STATE_COMPLETED
        json_result["processed_resources"].extend(new_processed_resources)
        # resources that are not processed after MAX RETRIES considered as failed
        json_result["failed_resources"].extend(new_unprocessed_resources)

        if json_result["processed_resources"]:  # check what resources were processed
            result_value = "true"
            output_message += (
                "Successfully scanned the following resources using {}:\n    {}".format(
                    INTEGRATION_NAME, "\n   ".join(json_result["processed_resources"])
                )
            )
            siemplify.result.add_result_json(
                {"resources": json_result["resources"]}  # add json results
            )
        else:
            output_message += "No resources were scanned."
            result_value = "false"

        if json_result["failed_resources"]:
            output_message += (
                "\n\nAction was not able to scan the following resources using {}:\n   "
                "{}").format(
                INTEGRATION_NAME, "\n   ".join(json_result["failed_resources"])
            )

    else:  # continue processing the rest unprocessed resources
        status = EXECUTION_STATE_INPROGRESS
        json_result["processed_resources"].extend(new_processed_resources)
        json_result["unprocessed_resources"] = new_unprocessed_resources
        json_result["retries"] = json_result["retries"] + 1
        output_message += (
            "Waiting for the following resources to be scanned using {}:\n    "
            "{}").format(
            INTEGRATION_NAME, "\n  ".join(json_result["unprocessed_resources"])
        )
        result_value = json.dumps(json_result)

    return output_message, result_value, status


@output_handler
def main(is_first_run):
    siemplify = SiemplifyAction()
    siemplify.script_name = f"{INTEGRATION_NAME} - {SCRIPT_NAME}"
    mode = "Main" if is_first_run else "Check changes"
    siemplify.LOGGER.info(f"================= {mode} - Param Init =================")

    # INIT INTEGRATION CONFIGURATION:
    aws_access_key = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="AWS Access Key ID",
        is_mandatory=True,
        print_value=True,
    )

    aws_secret_key = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="AWS Secret Key",
        is_mandatory=True,
    )

    aws_default_region = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="AWS Default Region",
        is_mandatory=True,
        print_value=True,
    )
    analyzer_name = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Analyzer Name",
        is_mandatory=True,
        print_value=True,
    )

    resources_arns = extract_action_param(
        siemplify, param_name="Resource ARNs", is_mandatory=True, print_value=True
    )

    siemplify.LOGGER.info(f"----------------- {mode} - Started -----------------")
    result_value = "false"
    output_message = ""

    try:
        resources_arns = load_csv_to_list(resources_arns, "Resources IDs")

        try:
            siemplify.LOGGER.info(f"Getting analyzer from {INTEGRATION_NAME} Service")
            manager = AWSIAMAnalyzerManager(
                aws_access_key=aws_access_key,
                aws_secret_key=aws_secret_key,
                aws_default_region=aws_default_region,
                analyzer_name=analyzer_name,
            )
            analyzer = manager.get_analyzer()
            siemplify.LOGGER.info(
                f"Successfully got analyzer from {INTEGRATION_NAME} Service"
            )
        except AWSIAMNotFoundException as e:
            raise AWSIAMAnalyzerNotFoundException(e)

        if is_first_run:
            # IAM Analyzer 'analyzedAt' timestamp granularity is in seconds. To avoid false negatives
            # when comparing analyzed timestamp with action's starting time (which is in milliseconds)
            # action's starting time is floored
            action_starting_time = int(unix_now() / 1000) * 1000
            siemplify.LOGGER.info(f"Action's starting time {action_starting_time}")
            output_message, result_value, status = submit_resources(
                siemplify,
                manager=manager,
                analyzer_arn=analyzer.arn,
                resource_arns=resources_arns,
                action_starting_time=action_starting_time,
            )
        else:
            output_message, result_value, status = get_analyzed_resources(
                siemplify, manager=manager, analyzer_arn=analyzer.arn
            )

    except AWSIAMAnalyzerNotFoundException as error:  # Analyzer not found exception
        siemplify.LOGGER.error(
            f"Error executing action '{SCRIPT_NAME}'. Reason: {analyzer_name} analyzer "
            "was not found"
        )
        siemplify.LOGGER.exception(error)
        status = EXECUTION_STATE_FAILED
        output_message += (
            f"Error executing action '{SCRIPT_NAME}'. Reason: {analyzer_name} "
            "analyzer was not found"
        )

    except Exception as error:  # action failed, stops playbook
        siemplify.LOGGER.error(
            f"Error executing action '{SCRIPT_NAME}'. Reason: {error}"
        )
        siemplify.LOGGER.exception(error)
        status = EXECUTION_STATE_FAILED
        output_message = f"Error executing action '{SCRIPT_NAME}'. Reason: {error}"

    siemplify.LOGGER.info(f"----------------- {mode} - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}:")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    is_first_run = len(sys.argv) < 3 or sys.argv[2] == "True"
    main(is_first_run)
