from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from ..core.MitreAttckManager import MitreAttckManager
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from TIPCommon import extract_configuration_param, extract_action_param, construct_csv
from soar_sdk.SiemplifyDataModel import InsightSeverity, InsightType

INTEGRATION_NAME = "MitreAttck"
SCRIPT_NAME = "Mitre Att&ck - Get Technique Details"
ID_IDENTIFIER = "ID"
EXTERNAL_ID_IDENTIFIER = "External ID"
PARAMETERS_DEFAULT_DELIMITER = ","


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = SCRIPT_NAME
    result_value = False
    status = EXECUTION_STATE_FAILED
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    # INIT INTEGRATION CONFIGURATION:
    api_root = extract_configuration_param(
        siemplify, provider_name=INTEGRATION_NAME, param_name="API Root"
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        default_value=True,
        input_type=bool,
        print_value=True,
    )

    # INIT ACTION PARAMETERS:
    identifiers = extract_action_param(
        siemplify,
        param_name="Technique Identifier",
        print_value=True,
        is_mandatory=True,
    )
    identifier_type = extract_action_param(
        siemplify,
        param_name="Identifier Type",
        print_value=True,
        is_mandatory=True,
        default_value=ID_IDENTIFIER,
    )
    create_insights = extract_action_param(
        siemplify, param_name="Create Insights", print_value=True, input_type=bool
    )

    identifiers_list = [
        i.strip() for i in identifiers.split(PARAMETERS_DEFAULT_DELIMITER)
    ]

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    try:
        manager = MitreAttckManager(api_root, verify_ssl)
        successful_identifiers = []
        failed_identifiers = []
        json_results = []
        output_message = ""

        for identifier in identifiers_list:
            siemplify.LOGGER.info(f"\n\nStarted processing identifier: {identifier}")

            if identifier_type == ID_IDENTIFIER:
                attack = manager.get_attack_by_id(identifier)
            elif identifier_type == EXTERNAL_ID_IDENTIFIER:
                attack = manager.get_attack_by_external_id(identifier)
            else:
                attack = manager.get_attack_by_name(identifier)

            if attack:
                siemplify.result.add_data_table(
                    title=f"{identifier} technique information",
                    data_table=construct_csv([attack.to_data_table()]),
                )
                if attack.url:
                    siemplify.result.add_link(
                        f"{identifier} technique link", attack.url
                    )

                json_results.append(attack)
                successful_identifiers.append(identifier)
                if create_insights:
                    if attack.description:
                        siemplify.create_case_insight(
                            triggered_by=INTEGRATION_NAME,
                            title=f"Technique Description - {identifier}",
                            content=attack.description,
                            entity_identifier="",
                            severity=InsightSeverity.INFO,
                            insight_type=InsightType.General,
                        )
                    else:
                        siemplify.LOGGER.info(
                            "Insight was not created for technique {}. Reason: description is "
                            "empty/not available".format(identifier)
                        )

                result_value = True
                siemplify.LOGGER.info(
                    f"Successfully retrieve information about identifier: {identifier}"
                )
            else:
                failed_identifiers.append(identifier)
                siemplify.LOGGER.error(
                    f"Action wasn't able to retrieve information about identifier: {identifier}"
                )

            siemplify.LOGGER.info(f"Finished processing identifier: {identifier}")

        if successful_identifiers:
            siemplify.result.add_result_json(
                [result.to_json() for result in json_results]
            )
            output_message += "\nRetrieved detailed information about the following techniques:\n{}".format(
                "\n".join(successful_identifiers)
            )
        if failed_identifiers:
            output_message += (
                "\nAction wasn't able to retrieve detailed information about the following techniques:"
                "\n{}".format("\n".join(failed_identifiers))
            )

        if not successful_identifiers:
            output_message += "\nAction wasn't able to find the provided techniques."

        status = EXECUTION_STATE_COMPLETED
    except Exception as e:
        siemplify.LOGGER.error("Error fetching Technique")
        siemplify.LOGGER.exception(e)
        output_message = f'Error executing action "Get Technique Details". Reason:{e}'

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  result_value: {result_value}\n  output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
