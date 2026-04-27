from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from ..core.MISPManager import MISPManager
from TIPCommon import extract_configuration_param, extract_action_param
from ..core.utils import string_to_multi_value
import arrow
from ..core.constants import (
    INTEGRATION_NAME,
    ATTRIBUTE_SEARCH_MAPPER,
    PROVIDED_EVENT,
    ALL_EVENTS,
    ADD_SIGHTING_TO_AN_ATTRIBUTE_SCRIPT_NAME,
    EXISTING_CATEGORY_TYPES,
)
from ..core.exceptions import (
    MISPManagerEventIdNotProvidedError,
    MISPNotAcceptableParamError,
    MISPManagerObjectUuidProvidedError,
    MISPManagerEventIdNotFoundError,
)


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = ADD_SIGHTING_TO_AN_ATTRIBUTE_SCRIPT_NAME

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
    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    ca_certificate = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="CA Certificate File - parsed into Base64 String",
    )
    # INIT ACTION PARAMETERS:
    event_id = extract_action_param(siemplify, param_name="Event ID", print_value=True)
    categories = string_to_multi_value(
        extract_action_param(siemplify, param_name="Category", print_value=True)
    )
    types = string_to_multi_value(
        extract_action_param(siemplify, param_name="Type", print_value=True)
    )
    sighting_type_text = extract_action_param(
        siemplify, param_name="Sightings Type", print_value=True, is_mandatory=True
    )
    source = extract_action_param(siemplify, param_name="Source", print_value=True)
    date_time = extract_action_param(
        siemplify, param_name="Date Time", print_value=True
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
    attribute_uuids = string_to_multi_value(
        extract_action_param(siemplify, param_name="Attribute UUID", print_value=True)
    )
    attribute_names = string_to_multi_value(
        extract_action_param(siemplify, param_name="Attribute Name", print_value=True)
    )
    id_type = ("ID" if event_id.isdigit() else "UUID") if event_id else None

    output_message = ""
    result_value = True
    status = EXECUTION_STATE_COMPLETED
    success_attributes, failed_attributes, json_results = [], [], []

    try:
        if set(map(str.lower, categories)).difference(set(EXISTING_CATEGORY_TYPES)):
            raise MISPNotAcceptableParamError(
                "Category",
                opt_msg=f'Acceptable values: {", ".join( [category.capitalize() for category in EXISTING_CATEGORY_TYPES])}',
            )

        if attribute_search == ATTRIBUTE_SEARCH_MAPPER[PROVIDED_EVENT] and not event_id:
            raise MISPManagerEventIdNotProvidedError(
                'Event ID needs to be provided, if "Provided Event" is selected '
                'for the parameter "Attribute Search"'
            )

        if (
            object_uuid
            and attribute_search == ATTRIBUTE_SEARCH_MAPPER[ALL_EVENTS]
            and not event_id
        ):
            raise MISPManagerObjectUuidProvidedError(
                'Event ID needs to be provided, if "Object UUID" is provided'
            )

        manager = MISPManager(api_root, api_token, use_ssl, ca_certificate)

        if attribute_search == ATTRIBUTE_SEARCH_MAPPER[PROVIDED_EVENT]:
            manager.get_event_by_id_or_raise(event_id)

        sighting_type_numeric = manager.get_sighting_type(sighting_type_text)

        iso_date = iso_time = None

        if date_time:
            try:
                parsed_datetime = arrow.get(date_time)
                iso_date, iso_time = (
                    parsed_datetime.date().isoformat(),
                    parsed_datetime.time().isoformat(),
                )
            except arrow.parser.ParserError as e:
                siemplify.LOGGER.exception(e)
                raise Exception("Invalid date time passed.")

        if object_uuid:
            attributes = manager.get_attributes_from_object(
                event_id=event_id,
                categories=categories,
                object_uuid=object_uuid,
                attribute_uuids=attribute_uuids,
                attribute_names=attribute_names,
                types=types,
            )
        else:
            attributes = manager.get_attributes(
                attribute_names=attribute_names,
                attribute_uuids=attribute_uuids,
                categories=categories,
                types=types,
                attribute_search=attribute_search,
                event_id=[event_id],
            )
        for attribute in attributes:
            attribute_uuid_or_value = (
                attribute.uuid if attribute_uuids else attribute.value
            )
            try:
                sighting = manager.add_sighting_to_attribute(
                    attribute_uuid=attribute.uuid,
                    date=iso_date,
                    time=iso_time,
                    source=source,
                    sighting_type=sighting_type_numeric,
                )
                if sighting:
                    success_attributes.append(attribute_uuid_or_value)
                    json_results.append(sighting)
                else:
                    failed_attributes.append(attribute_uuid_or_value)
            except Exception as e:
                failed_attributes.append(attribute_uuid_or_value)
                siemplify.LOGGER.error(
                    f"Error to add sighting to attribute '{attribute_uuid_or_value}'"
                )
                siemplify.LOGGER.exception(e)

        handled_attr_ids = success_attributes + failed_attributes

        # add not found obj uuids or values to failed list
        failed_attributes += [
            failed_attr
            for failed_attr in (attribute_uuids if attribute_uuids else attribute_names)
            if failed_attr not in handled_attr_ids
        ]

        if success_attributes:
            siemplify.result.add_result_json(
                [sighting.to_json() for sighting in json_results]
            )
            output_message += f'Successfully added sighting for the following attributes in {INTEGRATION_NAME}:\n {", ".join(success_attributes)}\n'

            if failed_attributes:
                output_message += f'Action didn’t add sighting for the following attributes in {INTEGRATION_NAME}:\n {", ".join(failed_attributes)}\n'
        else:
            output_message = f"No sightings were added for the provided attributes in {INTEGRATION_NAME}"
            result_value = False

    except Exception as e:
        output_message = f"Error executing action '{ADD_SIGHTING_TO_AN_ATTRIBUTE_SCRIPT_NAME}'. Reason: "
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
