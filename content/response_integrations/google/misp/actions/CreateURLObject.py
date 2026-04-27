from __future__ import annotations
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from ..core.MISPManager import MISPManager
from TIPCommon import extract_configuration_param, extract_action_param, construct_csv
from ..core.exceptions import MISPManagerEventIdNotFoundError, MISPMissingParamError
from ..core.utils import get_entity_original_identifier
from ..core.constants import (
    INTEGRATION_NAME,
    EVENT_URL_OBJECT_TABLE_NAME,
    CREATE_URL_OBJECT_SCRIPT_NAME,
)

SUPPORTED_ENTITY_TYPES = [EntityTypes.URL]


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = CREATE_URL_OBJECT_SCRIPT_NAME

    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    # INIT INTEGRATION CONFIGURATION:
    api_root = extract_configuration_param(
        siemplify, provider_name=INTEGRATION_NAME, param_name="Api Root"
    )

    api_token = extract_configuration_param(
        siemplify, provider_name=INTEGRATION_NAME, param_name="Api Key"
    )
    use_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Use SSL",
        default_value=False,
        input_type=bool,
    )
    ca_certificate = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="CA Certificate File - parsed into Base64 String",
    )
    # INIT ACTION PARAMETERS:
    event_id = extract_action_param(
        siemplify, param_name="Event ID", is_mandatory=True, print_value=True
    )
    url = extract_action_param(siemplify, param_name="URL", print_value=True)
    port = extract_action_param(siemplify, param_name="Port", print_value=True)
    first_seen = extract_action_param(
        siemplify, param_name="First seen", print_value=True
    )
    last_seen = extract_action_param(
        siemplify, param_name="Last seen", print_value=True
    )
    domain = extract_action_param(siemplify, param_name="Domain", print_value=True)
    text = extract_action_param(siemplify, param_name="Text", print_value=True)
    ip = extract_action_param(siemplify, param_name="IP", print_value=True)
    host = extract_action_param(siemplify, param_name="Host", print_value=True)
    use_entities = extract_action_param(
        siemplify,
        param_name="Use Entities",
        input_type=bool,
        default_value=False,
        print_value=True,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    id_type = "ID" if event_id.isdigit() else "UUID"

    result_value = True
    status = EXECUTION_STATE_COMPLETED
    output_message = ""
    success_created_objs, success_created_objs_urls, failed_objects = [], [], []
    misp_obj_params = {
        "event_id": event_id,
        "url": url,
        "port": port,
        "first_seen": first_seen,
        "last_seen": last_seen,
        "domain": domain,
        "text": text,
        "ip": ip,
        "host": host,
    }

    try:
        if not use_entities and not url:
            raise MISPMissingParamError(
                "Either 'URL' should be provided or 'Use Entities' parameter set to true"
            )

        manager = MISPManager(api_root, api_token, use_ssl, ca_certificate)
        manager.get_event_by_id_or_raise(event_id)
        all_params = []

        if use_entities:
            for entity_url in [
                get_entity_original_identifier(entity)
                for entity in siemplify.target_entities
                if entity.entity_type in SUPPORTED_ENTITY_TYPES
            ]:
                all_params.append({"event_id": event_id, "url": entity_url})
        else:
            all_params.append(misp_obj_params)

        for params in all_params:
            try:
                misp_obj = manager.add_url_object(**params)
                success_created_objs.append(misp_obj)
                success_created_objs_urls.append(params["url"])
            except Exception as e:
                siemplify.LOGGER.error(e)
                siemplify.LOGGER.exception(e)
                failed_objects.append((params["url"], str(e)))

        if success_created_objs:
            siemplify.result.add_result_json(
                [misp_obj.to_json() for misp_obj in success_created_objs]
            )
            all_attributes = []
            for misp_obj in success_created_objs:
                all_attributes.extend(misp_obj.attributes)

            siemplify.result.add_data_table(
                EVENT_URL_OBJECT_TABLE_NAME.format(event_id),
                construct_csv(
                    [attribute.to_base_csv() for attribute in all_attributes]
                ),
            )
        if use_entities:
            if success_created_objs:
                output_message = (
                    "Successfully created new URL objects for event with {} {} in {} "
                    "based on the following entities: \n{}\n".format(
                        id_type,
                        event_id,
                        INTEGRATION_NAME,
                        ", ".join(success_created_objs_urls),
                    )
                )

                if failed_objects:
                    output_message += (
                        "Action wasn’t able to create new URL objects for event with {}"
                        " {} in {} based on the following entities: \n{}".format(
                            id_type,
                            event_id,
                            INTEGRATION_NAME,
                            ", ".join(
                                [failed_url for (failed_url, e) in failed_objects]
                            ),
                        )
                    )
            else:
                result_value = False
                output_message = (
                    "Action wasn’t able to create new URL objects for event with {} {} in"
                    " {} based on the provided entities.".format(
                        id_type, event_id, INTEGRATION_NAME
                    )
                )
        else:
            if success_created_objs:
                output_message = f"Successfully created new URL object for event with {id_type} {event_id} in {INTEGRATION_NAME}."
            elif failed_objects:
                result_value = False
                failed_url, reason = failed_objects[0]
                output_message = (
                    "Action wasn’t able to created URL object for event with {} {} "
                    "in {}. Reason: {}".format(
                        id_type, event_id, INTEGRATION_NAME, reason
                    )
                )

    except Exception as e:
        output_message = (
            f"Error executing action '{CREATE_URL_OBJECT_SCRIPT_NAME}'. Reason: "
        )
        output_message += (
            f"Event with {id_type} {event_id} was not found in {INTEGRATION_NAME}"
            if isinstance(e, MISPManagerEventIdNotFoundError)
            else str(e)
        )
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = False

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  result_value: {result_value}\n  output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
