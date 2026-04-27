from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction
from TIPCommon import extract_configuration_param, extract_action_param, construct_csv
from ..core.VectraManager import VectraManager
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from ..core.constants import INTEGRATION_NAME, GET_TRIAGE_RULE_DETAILS_SCRIPT_NAME
from ..core.VectraExceptions import ItemNotFoundException

TABLE_HEADER = "Triage Rules Details"
INSIGHT_TITLE = "Triage Rule {}"
INSIGHT_DESCRIPTION = (
    "Detection Category: {}\n Triage Category: {}\n Detection: {} \n Description: {}"
)


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = GET_TRIAGE_RULE_DETAILS_SCRIPT_NAME
    result_value = True
    status = EXECUTION_STATE_COMPLETED
    output_message = ""
    successful_ids = []
    failed_ids = []
    detailed_triages = []

    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    # Configuration.
    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Root",
        input_type=str,
        is_mandatory=True,
    )
    api_token = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Token",
        input_type=str,
        is_mandatory=True,
        print_value=False,
        remove_whitespaces=False,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        default_value=True,
        input_type=bool,
        is_mandatory=True,
    )

    # Parameters
    triage_rule_ids = extract_action_param(
        siemplify,
        param_name="Triage Rule IDs",
        input_type=str,
        is_mandatory=True,
        print_value=True,
    )
    create_insights = extract_action_param(
        siemplify,
        param_name="Create Insights",
        input_type=bool,
        is_mandatory=False,
        print_value=True,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    try:
        vectra_manager = VectraManager(
            api_root=api_root,
            api_token=api_token,
            verify_ssl=verify_ssl,
            siemplify=siemplify,
        )

        triage_ids = [t.strip() for t in triage_rule_ids.split(",") if t.strip()]
        for triage_id in triage_ids:
            try:
                triage_object = vectra_manager.get_triage_rule_details(
                    triage_id=triage_id
                )
                detailed_triages.append(triage_object)
                successful_ids.append(triage_id)
                if create_insights:
                    siemplify.create_case_insight(
                        INTEGRATION_NAME,
                        INSIGHT_TITLE.format(triage_id),
                        INSIGHT_DESCRIPTION.format(
                            triage_object.detection_category,
                            triage_object.triage_category,
                            triage_object.detection,
                            triage_object.description,
                        ),
                        triage_id,
                        0,
                        0,
                    )
            except ItemNotFoundException:
                failed_ids.append(triage_id)

        if successful_ids:
            siemplify.result.add_result_json(
                [triage.to_json() for triage in detailed_triages]
            )
            siemplify.result.add_data_table(
                title=TABLE_HEADER,
                data_table=construct_csv(
                    [triage.to_csv() for triage in detailed_triages]
                ),
            )
            output_message = (
                "Successfully retrieved information about the following"
                " triage rules from Vectra: {}".format("\n".join(
                    [id for id in successful_ids]
                    )
                )
            )

        if failed_ids:
            output_message += (
                "\n\n Action was not able to retrieve information about the following"
                " triage rules: {}".format(
                "\n".join([ids for ids in failed_ids])
                )
            )

        if not successful_ids:
            output_message = "No information was retrieved about the triage rules."
            result_value = False

    except Exception as e:
        output_message = (
            f'Error executing action "Get Triage Rule Details". Reason: {e}'
        )
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = False

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")

    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
