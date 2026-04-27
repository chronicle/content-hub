from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler, convert_dict_to_json_result_dict
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.RSAManager import RSAManager
from TIPCommon import extract_configuration_param, construct_csv, extract_action_param
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from ..core.constants import (
    INTEGRATION_NAME,
    QUERY_NET_USER_ACTION,
    ATTACHMENT_NAME,
    DEFAULT_HOURS_BACKWARDS,
    DEFAULT_EVENTS_LIMIT,
)

SUPPORTED_ENTITY_TYPES = [EntityTypes.USER]


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = QUERY_NET_USER_ACTION
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    # Configuration
    broker_api_root = extract_configuration_param(
        siemplify, provider_name=INTEGRATION_NAME, param_name="Broker API Root"
    )
    broker_username = extract_configuration_param(
        siemplify, provider_name=INTEGRATION_NAME, param_name="Broker API Username"
    )
    broker_password = extract_configuration_param(
        siemplify, provider_name=INTEGRATION_NAME, param_name="Broker API Password"
    )
    concentrator_api_root = extract_configuration_param(
        siemplify, provider_name=INTEGRATION_NAME, param_name="Concentrator API Root"
    )
    concentrator_username = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Concentrator API Username",
    )
    concentrator_password = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Concentrator API Password",
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
    hours_backwards = extract_action_param(
        siemplify,
        param_name="Max Hours Backwards",
        default_value=DEFAULT_HOURS_BACKWARDS,
        input_type=int,
    )
    events_limit = extract_action_param(
        siemplify,
        param_name="Max Events To Return",
        default_value=DEFAULT_EVENTS_LIMIT,
        input_type=int,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    json_result = {}
    entities_with_result = []
    failed_entities = []
    result_value = False
    status = EXECUTION_STATE_COMPLETED
    output_message = ""
    suitable_entities = [
        entity
        for entity in siemplify.target_entities
        if entity.entity_type in SUPPORTED_ENTITY_TYPES
    ]

    try:
        rsa_manager = RSAManager(
            broker_api_root=broker_api_root,
            broker_username=broker_username,
            broker_password=broker_password,
            concentrator_api_root=concentrator_api_root,
            concentrator_username=concentrator_username,
            concentrator_password=concentrator_password,
            size=events_limit,
            verify_ssl=verify_ssl,
        )

        for entity in suitable_entities:
            try:
                siemplify.LOGGER.info(
                    f"\n\nStarted processing entity: {entity.identifier}"
                )

                events = rsa_manager.get_events_for_user(
                    entity.identifier, hours_backwards
                )
                if events:
                    json_result[entity.identifier] = [
                        event.to_json() for event in events
                    ]
                    siemplify.result.add_entity_table(
                        entity.identifier,
                        construct_csv([event.to_csv() for event in events]),
                    )

                    siemplify.result.add_entity_attachment(
                        entity.identifier,
                        ATTACHMENT_NAME.format(entity.identifier),
                        rsa_manager.get_pcap_for_user(
                            entity.identifier, hours_backwards
                        ),
                    )
                    entities_with_result.append(entity.identifier)
                    result_value = True
                siemplify.LOGGER.info(f"Found {len(events)} event(s)")
                siemplify.LOGGER.info(
                    f"Finished processing entity: {entity.identifier}"
                )
            except Exception as e:
                failed_entities.append(entity.identifier)
                siemplify.LOGGER.error(
                    f"Action was not able to processing entity :  \n {entity.identifier}"
                )
                siemplify.LOGGER.exception(e)

        if failed_entities:
            output_message += f'Events were not found for the following users: {", ".join(failed_entities)}.'

        if entities_with_result:
            output_message += f'Successfully found events in RSA NetWitness for the following users: {", ".join(entities_with_result)}.'
        else:
            output_message += "\n  No events were found."

        siemplify.result.add_result_json(convert_dict_to_json_result_dict(json_result))

    except Exception as e:
        output_message = f"Error executing action {QUERY_NET_USER_ACTION}. Reason: {e}"
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  result_value: {result_value}\n  output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
