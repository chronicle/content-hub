from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyAction import SiemplifyAction
from TIPCommon import extract_configuration_param, extract_action_param
from ..core.FireEyeCMManager import FireEyeCMManager
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from ..core.FireEyeCMExceptions import IncorrectHashTypeException
from ..core.UtilsManager import create_entities_file
from urllib.parse import urlparse
import base64
from ..core.FireEyeCMConstants import PROVIDER_NAME, ADD_IOC_FEED_SCRIPT_NAME, FEED_NAME

SUPPORTED_ENTITY_TYPES = [EntityTypes.ADDRESS, EntityTypes.URL, EntityTypes.FILEHASH]


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = ADD_IOC_FEED_SCRIPT_NAME
    result_value = True
    status = EXECUTION_STATE_COMPLETED
    output_messages = []
    json_results = []
    successful_entities = []
    failed_entities = []
    suitable_entities = [
        entity
        for entity in siemplify.target_entities
        if entity.entity_type in SUPPORTED_ENTITY_TYPES
    ]

    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    # Init Integration Configurations
    api_root = extract_configuration_param(
        siemplify,
        provider_name=PROVIDER_NAME,
        param_name="API Root",
        is_mandatory=True,
        print_value=True,
    )

    username = extract_configuration_param(
        siemplify,
        provider_name=PROVIDER_NAME,
        param_name="Username",
        is_mandatory=True,
        print_value=False,
    )

    password = extract_configuration_param(
        siemplify,
        provider_name=PROVIDER_NAME,
        param_name="Password",
        is_mandatory=True,
        print_value=False,
    )

    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=PROVIDER_NAME,
        param_name="Verify SSL",
        input_type=bool,
        is_mandatory=True,
        print_value=True,
    )

    # Init Action Parameters
    action_type = extract_action_param(
        siemplify, param_name="Action", is_mandatory=True, print_value=True
    )
    comment = extract_action_param(
        siemplify, param_name="Comment", is_mandatory=False, print_value=True
    )
    extract_domain = extract_action_param(
        siemplify,
        param_name="Extract Domain",
        is_mandatory=True,
        input_type=bool,
        print_value=True,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    try:
        manager = FireEyeCMManager(
            api_root=api_root,
            username=username,
            password=password,
            verify_ssl=verify_ssl,
            siemplify=siemplify,
        )

        for entity in suitable_entities:
            siemplify.LOGGER.info(f"Started processing entity: {entity.identifier}")
            if extract_domain and entity.entity_type == EntityTypes.URL:
                parsed_url = urlparse(entity.identifier)
                identifier = parsed_url.netloc
            else:
                identifier = entity.identifier
            feed_name = (
                FEED_NAME.format(base64.b64encode(identifier.encode()).decode())
            ).replace("=", "")
            try:
                entity_filepath = create_entities_file(
                    siemplify=siemplify, identifier=identifier
                )
                if entity_filepath:
                    manager.add_ioc_feed(
                        entity_type=entity.entity_type,
                        identifier=identifier,
                        action=action_type,
                        comment=comment,
                        extract_domain=extract_domain,
                        entity_file=entity_filepath,
                        feed_name=feed_name,
                    )
                else:
                    failed_entities.append(entity)
                json_results.append(feed_name)
                successful_entities.append(entity)
                siemplify.LOGGER.info(f"Successfully added new IOC feed {feed_name}")
            except IncorrectHashTypeException as e:
                failed_entities.append(entity)
                siemplify.LOGGER.exception(e)
            except Exception as e:
                failed_entities.append(entity)
                siemplify.LOGGER.error(
                    f"Something went wrong while adding new IOC feed {feed_name}"
                )
                siemplify.LOGGER.exception(e)

            siemplify.LOGGER.info(f"Finished processing entity: {entity.identifier}")

        if successful_entities:
            siemplify.result.add_result_json({"New_IOC_Feeds": json_results})
            output_messages.append(
                "Successfully added new IOC feeds to FireEye CM based on the following entities: "
                "{}".format(
                    "\n ".join([entity.identifier for entity in successful_entities])
                )
            )

        if failed_entities:
            output_messages.append(
                "Action wasn't able to create new IOC feeds in FireEye CM based on the following "
                "entities: {}".format(
                    "\n ".join([entity.identifier for entity in failed_entities])
                )
            )

        output_message = "\n".join(output_messages)

        if not successful_entities:
            output_message = "No IOC feeds were created in FireEye CM!"
            result_value = False

    except Exception as e:
        output_message = f'Error executing action "Add IOC Feed". Reason: {e}'
        siemplify.LOGGER.error(output_message)
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
