from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from ..core.MISPManager import MISPManager
from TIPCommon import extract_configuration_param, extract_action_param
from ..core.exceptions import (
    MISPManagerEventIdNotFoundError,
    MISPNotAcceptableParamError,
    MISPMissingParamError,
    MISPManagerObjectUuidProvidedError,
)
from ..core.utils import string_to_multi_value, adjust_categories
from ..core.constants import (
    DELETE_AN_ATTRIBUTE_SCRIPT_NAME,
    EXISTING_CATEGORY_TYPES,
    ATTRIBUTE_SEARCH_MAPPER,
    INTEGRATION_NAME,
    PROVIDED_EVENT,
)


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = DELETE_AN_ATTRIBUTE_SCRIPT_NAME

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

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    # INIT ACTION PARAMETERS:
    event_id = extract_action_param(siemplify, param_name="Event ID", print_value=True)
    categories = adjust_categories(
        string_to_multi_value(
            extract_action_param(siemplify, param_name="Category", print_value=True)
        )
    )
    attribute_types = string_to_multi_value(
        extract_action_param(siemplify, param_name="Type", print_value=True)
    )
    object_uuid = extract_action_param(
        siemplify, param_name="Object UUID", print_value=True
    )
    attribute_search = extract_action_param(
        siemplify,
        param_name="Attribute Search",
        print_value=True,
        default_value=ATTRIBUTE_SEARCH_MAPPER[PROVIDED_EVENT],
    )
    attribute_names = string_to_multi_value(
        extract_action_param(siemplify, param_name="Attribute Name", print_value=True)
    )
    attribute_uuids = string_to_multi_value(
        extract_action_param(siemplify, param_name="Attribute UUID", print_value=True)
    )
    id_type = ("ID" if event_id.isdigit() else "UUID") if event_id else None

    status = EXECUTION_STATE_COMPLETED
    result_value = True
    output_message = ""
    fetched_by_attr_uuids = bool(attribute_uuids)

    try:
        if set(map(str.lower, categories)).difference(set(EXISTING_CATEGORY_TYPES)):
            raise MISPNotAcceptableParamError(
                "Category",
                opt_msg=f'Acceptable values: {", ".join( [category.capitalize() for category in EXISTING_CATEGORY_TYPES])}',
            )

        if attribute_search == ATTRIBUTE_SEARCH_MAPPER[PROVIDED_EVENT] and not event_id:
            raise MISPMissingParamError(
                "Event ID needs to be provided, if '{}' is selected for the parameter "
                "'Attribute Search'.".format(ATTRIBUTE_SEARCH_MAPPER[PROVIDED_EVENT])
            )

        if (
            object_uuid
            and attribute_search == ATTRIBUTE_SEARCH_MAPPER["all"]
            and not event_id
        ):
            raise MISPManagerObjectUuidProvidedError(
                'Event ID needs to be provided, if "Object UUID" is provided'
            )

        api_messages = []
        success_deleted_attrs, failed_to_delete_attrs = [], []

        manager = MISPManager(api_root, api_token, use_ssl, ca_certificate)

        if attribute_search == ATTRIBUTE_SEARCH_MAPPER[PROVIDED_EVENT]:
            manager.get_event_by_id_or_raise(event_id)

        if object_uuid:
            attributes = manager.get_attributes_from_object(
                event_id=event_id,
                object_uuid=object_uuid,
                attribute_names=attribute_names,
                types=attribute_types,
                attribute_uuids=attribute_uuids,
                categories=categories,
            )
        else:
            attributes = manager.get_attributes(
                attribute_names=attribute_names,
                attribute_uuids=attribute_uuids,
                categories=categories,
                types=attribute_types,
                event_id=[event_id],
                attribute_search=attribute_search,
            )

        for attribute in attributes:
            attr_value_or_id = (
                attribute.uuid if fetched_by_attr_uuids else attribute.value
            )
            try:
                api_message = manager.delete_attribute(attribute.uuid)
                api_messages.append(api_message)
                success_deleted_attrs.append(attr_value_or_id)
            except Exception as e:
                siemplify.LOGGER.exception(e)
                failed_to_delete_attrs.append(attr_value_or_id)

        handled_attr_ids = success_deleted_attrs + failed_to_delete_attrs
        # add not found obj uuids to failed list
        for attr_uuid in attribute_uuids:
            if attr_uuid not in handled_attr_ids:
                failed_to_delete_attrs.append(attr_uuid)

        # add not found attr values to failed list
        if not attribute_uuids:
            for attr_name in attribute_names:
                if attr_name not in handled_attr_ids:
                    failed_to_delete_attrs.append(attr_name)

        if success_deleted_attrs:
            output_message += f'Successfully deleted the following attributes in {INTEGRATION_NAME}: \n{", ".join(success_deleted_attrs)}\n'
            if failed_to_delete_attrs:
                output_message += f'Action didn’t delete the following attributes in {INTEGRATION_NAME}: \n{", ".join(failed_to_delete_attrs)}'
        else:
            output_message += f"No attributes were deleted in {INTEGRATION_NAME}"
            result_value = False

        if api_messages:
            siemplify.result.add_result_json(
                [api_msg.to_json() for api_msg in api_messages]
            )

    except Exception as e:
        output_message = (
            f"Error executing action '{DELETE_AN_ATTRIBUTE_SCRIPT_NAME}'. Reason: "
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
