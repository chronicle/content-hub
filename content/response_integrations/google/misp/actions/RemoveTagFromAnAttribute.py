from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.utils import string_to_multi_value, adjust_categories
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from ..core.MISPManager import MISPManager, REMOVE_ACTION
from TIPCommon import extract_configuration_param, extract_action_param
from ..core.constants import (
    INTEGRATION_NAME,
    REMOVE_TAG_FROM_AN_ATTRIBUTE,
    ATTRIBUTE_SEARCH_MAPPER,
    EXISTING_CATEGORY_TYPES,
    ALL_EVENTS,
    PROVIDED_EVENT,
)
from ..core.exceptions import (
    MISPManagerEventIdNotFoundError,
    MISPManagerTagNotFoundError,
    MISPManagerInvalidCategoryError,
    MISPManagerEventIdNotProvidedError,
    MISPManagerObjectUuidProvidedError,
)


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = REMOVE_TAG_FROM_AN_ATTRIBUTE

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
    event_id = extract_action_param(siemplify, param_name="Event ID", print_value=True)
    tag_names = string_to_multi_value(
        extract_action_param(
            siemplify, param_name="Tag Name", print_value=True, is_mandatory=True
        )
    )
    attribute_names = string_to_multi_value(
        extract_action_param(siemplify, param_name="Attribute Name", print_value=True)
    )
    categories = adjust_categories(
        string_to_multi_value(
            extract_action_param(siemplify, param_name="Category", print_value=True)
        )
    )
    types = string_to_multi_value(
        extract_action_param(siemplify, param_name="Type", print_value=True)
    )
    attribute_search = extract_action_param(
        siemplify,
        param_name="Attribute Search",
        print_value=True,
        default_value=ATTRIBUTE_SEARCH_MAPPER[PROVIDED_EVENT],
    )
    attribute_uuids = string_to_multi_value(
        extract_action_param(siemplify, param_name="Attribute UUID", print_value=True)
    )
    object_uuid = extract_action_param(
        siemplify, param_name="Object UUID", print_value=True
    )
    id_type = None
    if event_id:
        id_type = "ID" if event_id.isdigit() else "UUID"

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    output_message = ""
    result_value = True
    status = EXECUTION_STATE_COMPLETED
    successful_attributes, failed_attributes, json_response, removed_tags = (
        [],
        [],
        [],
        [],
    )

    try:
        manager = MISPManager(api_root, api_token, use_ssl, ca_certificate)
        # Validations
        if attribute_search == ATTRIBUTE_SEARCH_MAPPER[PROVIDED_EVENT] and not event_id:
            raise MISPManagerEventIdNotProvidedError(
                'Event ID needs to be provided, if "Provided Event" is selected '
                'for the parameter "Attribute Search"'
            )

        if attribute_search == ATTRIBUTE_SEARCH_MAPPER[PROVIDED_EVENT] and event_id:
            event_id = manager.get_event_by_id_or_raise(event_id).id

        if len(
            [
                category
                for category in categories
                if category.lower() in EXISTING_CATEGORY_TYPES
            ]
        ) != len(categories):
            raise MISPManagerInvalidCategoryError(
                'Invalid value was provided for the parameter "Category". '
                "Acceptable values: {}.".format(
                    ", ".join(
                        [category.capitalize() for category in EXISTING_CATEGORY_TYPES]
                    )
                )
            )
        if (
            object_uuid
            and attribute_search == ATTRIBUTE_SEARCH_MAPPER[ALL_EVENTS]
            and not event_id
        ):
            raise MISPManagerObjectUuidProvidedError(
                'Event ID needs to be provided, if "Object UUID" is provided'
            )

        # Find tags
        existing_tag_names, not_existing_tag_names = manager.find_tags_with_names(
            tag_names
        )

        if not existing_tag_names:
            raise MISPManagerTagNotFoundError(
                "None of the provided tags were found in MISP."
            )

        if object_uuid:
            attributes = manager.get_attributes_from_object(
                event_id=event_id,
                object_uuid=object_uuid,
                attribute_names=attribute_names,
                attribute_uuids=attribute_uuids,
                categories=categories,
                types=types,
            )
        else:
            attributes = manager.get_attributes(
                attribute_names=attribute_names,
                attribute_uuids=attribute_uuids,
                categories=categories,
                types=types,
                attribute_search=attribute_search,
                event_id=event_id,
            )

        failed_attributes = list(
            set(attribute_names) - set([attribute.value for attribute in attributes])
        )

        for attribute in attributes:
            attribute_identifier = (
                attribute.uuid if attribute_uuids else attribute.value
            )
            try:
                for tag_name in existing_tag_names:
                    try:
                        json_response.append(
                            manager.add_remove_tag_to_attribute(
                                REMOVE_ACTION, tag_name, attribute.uuid
                            )
                        )
                        removed_tags.append(tag_name)
                    except Exception as e:
                        siemplify.LOGGER.error(
                            f"Error when removing tag '{tag_name}' from an attribute '{attribute_identifier}'"
                        )
                        siemplify.LOGGER.exception(e)
                successful_attributes.append(attribute_identifier)
            except Exception as e:
                failed_attributes.append(attribute_identifier)
                siemplify.LOGGER.error(
                    f"Error when removing tags from an attribute '{attribute_identifier}'"
                )
                siemplify.LOGGER.exception(e)

        if json_response:
            siemplify.result.add_result_json(
                [api_message.to_json() for api_message in json_response]
            )

        if successful_attributes:
            output_message += f"Successfully removed tags from the following attributes in {INTEGRATION_NAME}: \n {', '.join(successful_attributes)} \n"

            if failed_attributes:
                output_message += f"Action didn’t removed tags from the following attributes in {INTEGRATION_NAME}: \n {', '.join(failed_attributes)} \n"
            if not removed_tags:
                output_message = f"No tags were removed from the provided attributes in {INTEGRATION_NAME}\n"
                result_value = False

        else:
            output_message = f"No tags were removed from the provided attributes in {INTEGRATION_NAME}\n"
            result_value = False

        if not_existing_tag_names:
            if not existing_tag_names:
                output_message = (
                    f"None of the provided tags were found in {INTEGRATION_NAME}.\n"
                )
            else:
                output_message += f"The following tags were not found in {INTEGRATION_NAME}: \n {', '.join(not_existing_tag_names)} \n"

    except MISPManagerTagNotFoundError as e:
        siemplify.LOGGER.error(e)
        output_message = str(e)
        result_value = False

    except Exception as e:
        output_message = (
            f"Error executing action {REMOVE_TAG_FROM_AN_ATTRIBUTE}. Reason: "
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
