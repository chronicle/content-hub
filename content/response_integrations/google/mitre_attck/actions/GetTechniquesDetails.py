from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler, convert_dict_to_json_result_dict
from ..core.MitreAttckManager import MitreAttckManager
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from TIPCommon import extract_configuration_param, extract_action_param, construct_csv


INTEGRATION_NAME = "MitreAttck"
SCRIPT_NAME = "Mitre Att&ck - Get Techniques Details"
ID_IDENTIFIER = "ID"
EXTERNAL_ID_IDENTIFIER = "External ID"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = SCRIPT_NAME
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

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    result_value = True
    status = EXECUTION_STATE_COMPLETED
    output_message = ""
    json_result = {}
    failed_identifiers = []
    succeeded_identifiers = []

    try:
        # Split techniques IDs
        identifiers = (
            [identifier.strip() for identifier in identifiers.split(",")]
            if identifiers
            else []
        )

        manager = MitreAttckManager(api_root, verify_ssl)

        if not manager.test_connectivity():
            output_message = "Unable to connect to MitreAttack"
            status = EXECUTION_STATE_FAILED
            result_value = "false"
        else:
            for identifier in identifiers:
                try:
                    siemplify.LOGGER.info(f"Processing technique {identifier}")

                    if identifier_type == ID_IDENTIFIER:
                        siemplify.LOGGER.info("Fetching attack by ID.")
                        attack = manager.get_attack_by_id(identifier)
                    elif identifier_type == EXTERNAL_ID_IDENTIFIER:
                        siemplify.LOGGER.info("Fetching attack by external ID.")
                        attack = manager.get_attack_by_external_id(identifier)
                    else:
                        siemplify.LOGGER.info("Fetching attack by name.")
                        attack = manager.get_attack_by_name(identifier)

                    if attack:
                        siemplify.LOGGER.info(
                            f"Found technique information for {identifier}"
                        )
                        siemplify.result.add_data_table(
                            title=f"{identifier} technique information",
                            data_table=construct_csv([attack.to_data_table()]),
                        )
                        if attack.url:
                            siemplify.result.add_link(
                                f"{identifier} technique link", attack.url
                            )

                        json_result[identifier] = attack.to_json()
                        succeeded_identifiers.append(identifier)

                    else:
                        siemplify.LOGGER.info(f"{identifier} technique was not found.")
                        failed_identifiers.append(identifier)

                except Exception as e:
                    siemplify.LOGGER.error(
                        f"An error occurred on Technique {identifier}"
                    )
                    siemplify.LOGGER.exception(e)
                    failed_identifiers.append(identifier)

            if succeeded_identifiers:
                output_message += "Successfully retrieved detailed information for for the following techniques:\n   {}".format(
                    "\n   ".join(succeeded_identifiers)
                )

            else:
                output_message += "No techniques were found."
                result_value = False

            if failed_identifiers:
                output_message += "\n\nAction wasn't able to find information for the following techniques:\n   {}".format(
                    "\n   ".join(failed_identifiers)
                )

    except Exception as e:
        siemplify.LOGGER.error("Error fetching techniques.")
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = False
        output_message = f'Error executing action "Get Technique Details". Reason: {e}'

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.result.add_result_json(convert_dict_to_json_result_dict(json_result))
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  result_value: {result_value}\n  output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
