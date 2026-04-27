from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from ..core.MISPManager import MISPManager
from TIPCommon import extract_configuration_param, extract_action_param, construct_csv
from ..core.utils import string_to_multi_value, adjust_categories
from itertools import chain
from ..core.constants import (
    INTEGRATION_NAME,
    LIST_SIGHTINGS_OF_AN_ATTRIBUTE_SCRIPT_NAME,
    EXISTING_CATEGORY_TYPES,
    PROVIDED_EVENT,
    ATTRIBUTE_LIST_SIGHTINGS_TABLE_NAME,
    ATTRIBUTE_SEARCH_MAPPER,
)
from ..core.exceptions import (
    MISPManagerEventIdNotProvidedError,
    MISPNotAcceptableParamError,
    MISPManagerEventIdNotFoundError,
)


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = LIST_SIGHTINGS_OF_AN_ATTRIBUTE_SCRIPT_NAME
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
    # INIT ACTION PARAMETERS:
    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    event_id = extract_action_param(siemplify, param_name="Event ID", print_value=True)
    attribute_names = string_to_multi_value(
        extract_action_param(siemplify, param_name="Attribute Name", print_value=True)
    )
    categories = adjust_categories(
        string_to_multi_value(
            extract_action_param(siemplify, param_name="Category", print_value=True)
        )
    )
    attribute_types = string_to_multi_value(
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
    id_type = ("ID" if event_id.isdigit() else "UUID") if event_id else None

    output_message = ""
    result_value = True
    status = EXECUTION_STATE_COMPLETED
    successful_attributes, failed_attributes, sightings_with_attribute = [], [], {}

    try:
        # Validations
        if attribute_search == ATTRIBUTE_SEARCH_MAPPER[PROVIDED_EVENT] and not event_id:
            raise MISPManagerEventIdNotProvidedError(
                'Event ID needs to be provided, if "Provided Event" is selected '
                'for the parameter "Attribute Search"'
            )

        if set(map(str.lower, categories)).difference(set(EXISTING_CATEGORY_TYPES)):
            raise MISPNotAcceptableParamError(
                "Category",
                opt_msg=f'Acceptable values: {", ".join( [category.capitalize() for category in EXISTING_CATEGORY_TYPES])}',
            )

        manager = MISPManager(api_root, api_token, use_ssl, ca_certificate)

        if attribute_search == ATTRIBUTE_SEARCH_MAPPER[PROVIDED_EVENT]:
            event_id = manager.get_event_by_id_or_raise(event_id).id

        for attribute in manager.get_attributes(
            attribute_names=attribute_names,
            attribute_uuids=attribute_uuids,
            attribute_search=attribute_search,
            event_id=[event_id],
            categories=categories,
            types=attribute_types,
        ):
            attribute_identifier = (
                attribute.uuid if attribute_uuids else attribute.value
            )
            try:
                sightings = manager.list_attribute_sightings(attribute.id)
                if sightings:
                    sightings_with_attribute[attribute] = sightings
                    successful_attributes.append(attribute_identifier)
                else:
                    siemplify.LOGGER.error(
                        f"Not found sightings from an attribute '{attribute_identifier}'"
                    )
                    failed_attributes.append(attribute_identifier)
            except Exception as e:
                failed_attributes.append(attribute_identifier)
                siemplify.LOGGER.error(
                    f"Error searching sightings from an attribute '{attribute_identifier}'"
                )
                siemplify.LOGGER.exception(e)

        handled_attr_ids = successful_attributes + failed_attributes

        # add not found obj uuids or values to failed list
        failed_attributes += [
            failed_attr
            for failed_attr in (attribute_uuids if attribute_uuids else attribute_names)
            if failed_attr not in handled_attr_ids
        ]

        merged_sightings_with_attr_name = {}
        for attr, attr_sightings in sightings_with_attribute.items():
            if not merged_sightings_with_attr_name.get(attr.value):
                merged_sightings_with_attr_name[attr.value] = []

            merged_sightings_with_attr_name[attr.value].extend(attr_sightings)

        if merged_sightings_with_attr_name:
            siemplify.result.add_result_json(
                [
                    sighting.to_json()
                    for sighting in chain.from_iterable(
                        merged_sightings_with_attr_name.values()
                    )
                ]
            )

        for attr_name, attr_sightings in merged_sightings_with_attr_name.items():
            siemplify.result.add_data_table(
                ATTRIBUTE_LIST_SIGHTINGS_TABLE_NAME.format(attr_name),
                construct_csv([sighting.to_csv() for sighting in attr_sightings]),
            )

        if successful_attributes:
            output_message += f"Successfully listed sightings for the following attributes in {INTEGRATION_NAME}:\n {', '.join(successful_attributes)}\n"

            if failed_attributes:
                output_message += f"Action didn’t list sightings for the following attributes in {INTEGRATION_NAME}: \n {', '.join(failed_attributes)} \n"
        else:
            output_message = f"No sightings were found for the provided attributes in {INTEGRATION_NAME}"
            result_value = False

    except Exception as e:
        output_message = f"Error executing action '{LIST_SIGHTINGS_OF_AN_ATTRIBUTE_SCRIPT_NAME}'. Reason: "
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
