from __future__ import annotations
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from ..core.MISPManager import MISPManager
from TIPCommon import extract_configuration_param, extract_action_param, construct_csv
from ..core.utils import get_entity_original_identifier, get_hash_type
from ..core.exceptions import MISPMissingParamError, MISPManagerEventIdNotFoundError
from ..core.constants import (
    INTEGRATION_NAME,
    FILE_OBJECT_TABLE_NAME,
    CREATE_FILE_OBJECT_SCRIPT_NAME,
)

SUPPORTED_ENTITY_TYPES = [EntityTypes.FILEHASH, EntityTypes.FILENAME]
SUPPORTED_HASH_TYPES = ["md5", "sha1", "sha256", "ssdeep"]


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = CREATE_FILE_OBJECT_SCRIPT_NAME
    siemplify.LOGGER.info("================= Main - Param Init =================")

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
    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    # INIT ACTION PARAMETERS:
    event_id = extract_action_param(
        siemplify, param_name="Event ID", is_mandatory=True, print_value=True
    )
    filename = extract_action_param(siemplify, param_name="FILENAME", print_value=True)
    md5 = extract_action_param(siemplify, param_name="MD5", print_value=True)
    sha1 = extract_action_param(siemplify, param_name="SHA1", print_value=True)
    sha256 = extract_action_param(siemplify, param_name="SHA256", print_value=True)
    ssdeep = extract_action_param(siemplify, param_name="SSDEEP", print_value=True)
    use_entities = extract_action_param(
        siemplify,
        param_name="Use Entities",
        input_type=bool,
        default_value=False,
        print_value=True,
    )
    id_type = "ID" if event_id.isdigit() else "UUID"

    result_value = True
    status = EXECUTION_STATE_COMPLETED
    output_message = ""
    success_created_objs, success_entities_values, failed_objects = [], [], []

    try:
        if not use_entities and not (filename or md5 or sha1 or sha256 or ssdeep):
            raise MISPMissingParamError(
                "One of the: 'FILENAME', 'MD5', 'SHA1', 'SHA256', 'SSDEEP' should be provided or 'Use Entities' "
                "parameter set to true"
            )

        manager = MISPManager(api_root, api_token, use_ssl, ca_certificate)

        manager.get_event_by_id_or_raise(event_id)

        all_params = []

        misp_obj_params = {
            "event_id": event_id,
            "filename": filename,
            "md5": md5,
            "sha1": sha1,
            "sha256": sha256,
            "ssdeep": ssdeep,
        }

        if use_entities:
            for entity in [
                entity
                for entity in siemplify.target_entities
                if entity.entity_type in SUPPORTED_ENTITY_TYPES
            ]:
                entity_identifier = get_entity_original_identifier(entity)

                if entity.entity_type == EntityTypes.FILEHASH:
                    hash_type = get_hash_type(entity_identifier)
                    if hash_type in SUPPORTED_HASH_TYPES:
                        all_params.append(
                            {
                                hash_type: entity_identifier,
                                "event_id": event_id,
                                "entity_identifier": entity_identifier,
                            }
                        )
                    else:
                        msg = "Hash type is not supported"
                        siemplify.LOGGER.info(msg)
                        failed_objects.append((entity_identifier, msg))

                elif entity.entity_type == EntityTypes.FILENAME:
                    all_params.append(
                        {
                            "event_id": event_id,
                            "filename": entity_identifier,
                            "entity_identifier": entity_identifier,
                        }
                    )
        else:
            all_params.append(misp_obj_params)

        for params in all_params:
            entity_identifier = (
                params.pop("entity_identifier")
                if params.get("entity_identifier")
                else None
            )
            try:
                misp_obj = manager.add_file_object(**params)
                success_created_objs.append(misp_obj)
                if entity_identifier:
                    success_entities_values.append(entity_identifier)
            except Exception as e:
                siemplify.LOGGER.error(e)
                siemplify.LOGGER.exception(e)
                failed_objects.append((entity_identifier, str(e)))

        if success_created_objs:
            siemplify.result.add_result_json(
                [misp_obj.to_json() for misp_obj in success_created_objs]
            )
            all_attributes = []
            for misp_obj in success_created_objs:
                all_attributes.extend(misp_obj.attributes)

            siemplify.result.add_data_table(
                FILE_OBJECT_TABLE_NAME.format(event_id),
                construct_csv(
                    [attribute.to_base_csv() for attribute in all_attributes]
                ),
            )

        if use_entities:
            if success_created_objs:
                output_message = (
                    "Successfully created new file objects for event with {} {} in {} "
                    "based on the following entities: \n{}\n".format(
                        id_type,
                        event_id,
                        INTEGRATION_NAME,
                        ", ".join(success_entities_values),
                    )
                )

                if failed_objects:
                    output_message += (
                        "Action wasn’t able to create new file objects for event with {}"
                        " {} in {} based on the following entities: \n{}".format(
                            id_type,
                            event_id,
                            INTEGRATION_NAME,
                            ", ".join([failed_id for (failed_id, e) in failed_objects]),
                        )
                    )
            else:
                result_value = False
                output_message = (
                    "Action wasn’t able to create new file objects for event with {} {} in"
                    " {} based on the provided entities.".format(
                        id_type, event_id, INTEGRATION_NAME
                    )
                )
        else:
            if success_created_objs:
                output_message = f"Successfully created new file object for event with {id_type} {event_id} in {INTEGRATION_NAME}."
            elif failed_objects:
                result_value = False
                failed_id, reason = failed_objects[0]
                output_message = (
                    "Action wasn’t able to created new file object for event with {} {} "
                    "in {}. Reason: {}".format(
                        id_type, event_id, INTEGRATION_NAME, reason
                    )
                )

    except Exception as e:
        output_message = (
            f"Error executing action '{CREATE_FILE_OBJECT_SCRIPT_NAME}'. Reason: "
        )
        output_message += (
            f"Event with {id_type} {event_id} was not found in {INTEGRATION_NAME}"
            if isinstance(e, MISPManagerEventIdNotFoundError)
            else str(e)
        )
        status = EXECUTION_STATE_FAILED
        result_value = False
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  result_value: {result_value}\n  output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
