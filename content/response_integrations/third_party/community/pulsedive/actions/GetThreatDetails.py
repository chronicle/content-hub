from __future__ import annotations

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.Siemplify import InsightSeverity, InsightType
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import convert_dict_to_json_result_dict, output_handler
from TIPCommon import construct_csv, extract_action_param, extract_configuration_param

from ..core.constants import GET_THREAT_SCRIPT_NAME, INTEGRATION_NAME
from ..core.exceptions import (
    ForceRaiseException,
    PulsediveLimitReachedException,
    PulsediveNotFoundException,
)
from ..core.PulsediveManager import PulsediveManager


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = GET_THREAT_SCRIPT_NAME

    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Root",
    )
    api_key = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Key",
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        default_value=True,
        input_type=bool,
    )

    threat_name = extract_action_param(
        siemplify,
        param_name="Threat Name",
        is_mandatory=False,
        input_type=str,
    )
    threat_id = extract_action_param(
        siemplify,
        param_name="Threat ID",
        is_mandatory=False,
        input_type=str,
    )
    split_risk = extract_action_param(
        siemplify,
        param_name="Split Risk",
        is_mandatory=False,
        input_type=bool,
    )
    retrieve_comments = extract_action_param(
        siemplify,
        param_name="Retrieve Comments",
        is_mandatory=False,
        input_type=bool,
    )
    create_insight = extract_action_param(
        siemplify,
        param_name="Create Insight",
        is_mandatory=False,
        input_type=bool,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    status = EXECUTION_STATE_COMPLETED
    json_results = {}
    result_value = "false"
    output_message = ""
    threat_data = {}

    result_value, output_message = False, ""

    try:
        manager = PulsediveManager(
            api_root=api_root,
            api_key=api_key,
            verify_ssl=verify_ssl,
        )

        siemplify.LOGGER.info(
            f"Started processing threat: {threat_name if threat_name else threat_id}",
        )
        try:
            if threat_name:
                threat_data = manager.get_threats(
                    threat_name=threat_name,
                    retrieve_comments=retrieve_comments,
                    split_risk=split_risk,
                )
            elif threat_id:
                threat_data = manager.get_threats(
                    threat_id=threat_id,
                    retrieve_comments=retrieve_comments,
                    split_risk=split_risk,
                )
            else:
                raise

            if threat_data:
                result_value = True

                # Create case wall table for comments
                if threat_data.threat_comments:
                    comments_table = construct_csv(
                        [comment.to_table() for comment in threat_data.threat_comments],
                    )
                    siemplify.result.add_data_table(
                        title=f"Comments: {threat_data.threat_name}",
                        data_table=comments_table,
                    )

                # Fill json with every entity data
                json_results[threat_data.threat_name] = threat_data.to_json(
                    comments=threat_data.threat_comments,
                    news=threat_data.threat_news,
                )

                if create_insight:
                    siemplify.create_case_insight(
                        triggered_by=INTEGRATION_NAME,
                        title="Threat Details",
                        content=threat_data.to_insight(),
                        entity_identifier=threat_data.threat_name,
                        severity=InsightSeverity.INFO,
                        insight_type=InsightType.General,
                    )
            else:
                output_message = "No threat details were retrieved."
                result_value = False

            siemplify.LOGGER.info(
                f"Finished processing threat {threat_data.threat_name}",
            )

        except Exception as e:
            if isinstance(e, ForceRaiseException):
                raise
            if isinstance(e, PulsediveNotFoundException):
                output_message = "No threat details found."
            if isinstance(e, PulsediveLimitReachedException):
                output_message = "Pulsedive limit exceeded."

            siemplify.LOGGER.error(f"An error occurred on threat name/id {threat_name}")
            siemplify.LOGGER.exception(e)

        if json_results:
            output_message = f"Successfully retrieved threat details for:\n{threat_name if threat_name else threat_id}"
            result = {"results": convert_dict_to_json_result_dict(json_results)}
            siemplify.result.add_result_json(result)

    except Exception as err:
        output_message = f"Error executing action “Get Threat Details”. Reason: {err}"
        result_value = False
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(err)

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}:")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
