from __future__ import annotations
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.McAfeeMvisionEDRV2Manager import McAfeeMvisionEDRV2Manager
from soar_sdk.SiemplifyUtils import output_handler, convert_dict_to_json_result_dict
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from TIPCommon import extract_configuration_param, extract_action_param, construct_csv
from ..core.constants import (
    CREATE_INVESTIGATION_SCRIPT_NAME,
    INTEGRATION_NAME,
    DEFAULT_INVESTIGATION_NAME,
)
import time


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = CREATE_INVESTIGATION_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    # Configuration
    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Root",
        is_mandatory=True,
    )

    iam_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="IAM Root",
        is_mandatory=True,
    )

    client_id = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Client ID",
        is_mandatory=True,
    )
    client_secret = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Client Secret",
        is_mandatory=True,
    )
    api_key = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Key",
        is_mandatory=True,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        default_value=True,
        input_type=bool,
    )

    scopes = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Scopes",
        is_mandatory=True,
    )

    # Parameters
    name = extract_action_param(
        siemplify,
        param_name="Name",
        is_mandatory=False,
        default_value=DEFAULT_INVESTIGATION_NAME,
    )
    hint = extract_action_param(siemplify, param_name="Hint", is_mandatory=False)
    priority = extract_action_param(siemplify, param_name="Priority", is_mandatory=True)
    case_type = extract_action_param(
        siemplify, param_name="Case Type", is_mandatory=True
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    status = EXECUTION_STATE_COMPLETED
    result_value = True
    successful_entities = []
    failed_entities = []
    json_results = {}
    output_message = ""

    try:
        siemplify.LOGGER.info("Connecting to McAfee Mvision EDR V2.")
        manager = McAfeeMvisionEDRV2Manager(
            api_root,
            iam_root,
            client_id,
            client_secret,
            api_key,
            scopes,
            verify_ssl,
            siemplify.LOGGER,
        )
        siemplify.LOGGER.info("Successfully connected to McAfee Mvision EDR V2.")

        investigations = []

        for entity in siemplify.target_entities:
            try:
                siemplify.LOGGER.info(f"Started processing entity: {entity.identifier}")

                if entity.entity_type == EntityTypes.ADDRESS:
                    investigation = manager.create_ip_investigation(
                        case_priority=priority,
                        case_type=case_type,
                        case_name=name,
                        case_hint=hint,
                        address=entity.identifier,
                    )

                elif entity.entity_type == EntityTypes.HOSTNAME:
                    investigation = manager.create_hostname_investigation(
                        case_priority=priority,
                        case_type=case_type,
                        case_name=name,
                        case_hint=hint,
                        hostname=entity.identifier,
                    )

                else:
                    siemplify.LOGGER.info(
                        f"Entity {entity.identifier} is of unsupported type. Skipping."
                    )
                    continue

                investigations.append(investigation)

                siemplify.LOGGER.info(
                    f"Created investigation {investigation.investigation_id} for entity {entity.identifier}."
                )

                json_results[entity.identifier] = investigation.to_json()
                successful_entities.append(entity.identifier)

                if hint:
                    # Sleep to avoid 429 rate limit errors on evidence adding
                    time.sleep(10)

            except Exception as e:
                failed_entities.append(entity.identifier)
                siemplify.LOGGER.error(
                    f"An error occurred on entity: {entity.identifier}"
                )
                siemplify.LOGGER.exception(e)

            siemplify.LOGGER.info(f"Finished processing entity: {entity.identifier}")

        if investigations:
            siemplify.result.add_data_table(
                title="Investigations",
                data_table=construct_csv(
                    [investigation.to_table_data() for investigation in investigations]
                ),
            )

        if successful_entities:
            output_message += "Successfully created investigation for the following entities: \n{}".format(
                "\n".join(successful_entities)
            )

        else:
            output_message = "No investigations were created."
            result_value = False

        if failed_entities:
            output_message += "\n\nAction was not able to create investigations for the following entities: \n{}\n".format(
                "\n".join(failed_entities)
            )

    except Exception as e:
        output_message = (
            f"Error executing action '{CREATE_INVESTIGATION_SCRIPT_NAME}'. Reason: {e}"
        )
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = False

    siemplify.result.add_result_json(convert_dict_to_json_result_dict(json_results))
    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  result_value: {result_value}\n  output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
