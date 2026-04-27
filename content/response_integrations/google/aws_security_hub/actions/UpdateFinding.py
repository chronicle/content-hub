from __future__ import annotations
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from TIPCommon import extract_configuration_param, extract_action_param
from ..core import consts
from ..core.AWSSecurityHubManager import AWSSecurityHubManager
from ..core.UtilsManager import get_mapped_value, load_csv_to_list, load_kv_csv_to_dict
from ..core.consts import INTEGRATION_NAME
from ..core.exceptions import (
    AWSSecurityHubStatusCodeException,
    AWSSecurityHubValidationException,
    AWSSecurityHubCriticalValidationException,
)

SCRIPT_NAME = "UpdateFinding"
DEFAULT_DDL_VALUE = "Select One"  # default value in drop down list


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = f"{INTEGRATION_NAME} - {SCRIPT_NAME}"
    siemplify.LOGGER.info("================= Main - Param Init =================")

    # INIT INTEGRATION CONFIGURATION:
    aws_access_key = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="AWS Access Key ID",
        is_mandatory=True,
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
    )

    finding_id = extract_action_param(
        siemplify, param_name="ID", is_mandatory=True, print_value=True
    )

    product_arn = extract_action_param(
        siemplify, param_name="Product ARN", is_mandatory=True, print_value=True
    )

    note_text = extract_action_param(
        siemplify, param_name="Note", is_mandatory=False, print_value=True
    )
    note_author = extract_action_param(
        siemplify, param_name="Note Author", is_mandatory=False, print_value=True
    )

    severity = extract_action_param(
        siemplify,
        param_name="Severity",
        is_mandatory=False,
        print_value=True,
        default_value=None,
    )

    verification_state = extract_action_param(
        siemplify,
        param_name="Verification State",
        is_mandatory=False,
        print_value=True,
        default_value=None,
    )

    confidence = extract_action_param(
        siemplify,
        param_name="Confidence",
        is_mandatory=False,
        print_value=True,
        input_type=int,
        default_value=None,
    )

    criticality = extract_action_param(
        siemplify,
        param_name="Criticality",
        is_mandatory=False,
        print_value=True,
        input_type=int,
        default_value=None,
    )

    types = extract_action_param(
        siemplify, param_name="Types", is_mandatory=False, print_value=True
    )

    workflow_status = extract_action_param(
        siemplify,
        param_name="Workflow Status",
        is_mandatory=False,
        print_value=True,
        default_value=None,
    )

    custom_fields = extract_action_param(
        siemplify, param_name="Custom Fields", is_mandatory=False, print_value=True
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    result_value = "true"
    output_message = ""
    status = EXECUTION_STATE_COMPLETED

    try:
        if (confidence and confidence not in consts.CONFIDENCE_CRITICALITY_RANGE) or (
            criticality and criticality not in consts.CONFIDENCE_CRITICALITY_RANGE
        ):
            raise AWSSecurityHubCriticalValidationException(
                "Confidence and criticality value should be in range from "
                f"{consts.CONFIDENCE_CRITICALITY_RANGE[0]} to "
                f"{consts.CONFIDENCE_CRITICALITY_RANGE[-1]}"
            )

        if (
            note_text or note_author
        ):  # validate both note_text and note_author. Both should exist if one of them exists
            if not (note_author and note_text):
                raise AWSSecurityHubCriticalValidationException(
                    "'Note' and 'Note Author' should be both specified."
                )

        verification_state = get_mapped_value(
            consts.MAPPED_VERIFICATION_STATE, verification_state, DEFAULT_DDL_VALUE
        )
        severity = get_mapped_value(consts.MAPPED_SEVERITY, severity, DEFAULT_DDL_VALUE)
        workflow_status = get_mapped_value(
            consts.MAPPED_WORKFLOW_STATUS, workflow_status, DEFAULT_DDL_VALUE
        )

        types = load_csv_to_list(csv=types, param_name="Types") if types else None
        custom_fields = (
            load_kv_csv_to_dict(kv_csv=custom_fields, param_name="Custom Fields")
            if custom_fields
            else None
        )

        siemplify.LOGGER.info("Connecting to AWS Security Hub Service")
        hub_client = AWSSecurityHubManager(
            aws_access_key=aws_access_key,
            aws_secret_key=aws_secret_key,
            aws_default_region=aws_default_region,
        )
        hub_client.test_connectivity()  # this validates the credentials
        siemplify.LOGGER.info("Successfully connected to AWS Security Hub service")

        siemplify.LOGGER.info(f"Updating finding {finding_id}")
        processed_finding, unprocessed_finding = hub_client.update_finding(
            finding_id=finding_id,
            product_arn=product_arn,
            note_text=note_text,
            note_author=note_author,
            severity=severity,
            verification_state=verification_state,
            workflow_status=workflow_status,
            confidence=confidence,
            criticality=criticality,
            types=types,
            custom_fields=custom_fields,
        )

        if not unprocessed_finding:  # if no unprocessed entries, action succeeded
            siemplify.LOGGER.info(
                f"Successfully updated finding with ID {processed_finding.finding_id} "
                f"and Product ARN {processed_finding.product_arn} in AWS Security Hub"
            )
            output_message += (
                f"Successfully updated finding with ID {processed_finding.finding_id} "
                f"and Product ARN {processed_finding.product_arn} in AWS Security Hub"
            )
        elif (
            unprocessed_finding and unprocessed_finding.error_code
        ):  # error code must exist in unprocessed finding to give error message
            result_value = "false"
            siemplify.LOGGER.error(
                f"Action wasn’t able to update finding with ID {finding_id} and "
                f"Product ARN {product_arn} in AWS Security Hub. "
                f"Reason: {unprocessed_finding.error_message}"
            )
            siemplify.LOGGER.exception(unprocessed_finding.error_message)
            output_message += (
                f"Action wasn’t able to update finding with ID {finding_id} and "
                f"Product ARN {product_arn} in AWS Security Hub. "
                f"Reason: {unprocessed_finding.error_message}"
            )
        else:  # critical error in aws security hub response
            raise AWSSecurityHubCriticalValidationException(
                "Failed to validate error code in unprocessed finding "
                f"{unprocessed_finding.finding_id} and Product ARN "
                f"{unprocessed_finding.product_arn}"
            )

    except (
        AWSSecurityHubStatusCodeException,
        AWSSecurityHubValidationException,
    ) as error:
        result_value = "false"
        siemplify.LOGGER.error(
            f"Action wasn’t able to update finding with ID {finding_id} and "
            f"Product ARN {product_arn} in AWS Security Hub. Reason: {error}"
        )
        siemplify.LOGGER.exception(error)
        output_message += (
            f"Action wasn’t able to update finding with ID {finding_id} and "
            f"Product ARN {product_arn} in AWS Security Hub. Reason: {error}"
        )

    except Exception as error:  # action failed, stops playbook
        siemplify.LOGGER.error(
            f"Error executing action 'Update Finding'. Reason: {error}"
        )
        siemplify.LOGGER.exception(error)
        status = EXECUTION_STATE_FAILED
        result_value = "false"
        output_message = f"Error executing action 'Update Finding'. Reason: {error}"

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}:")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
