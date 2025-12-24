from __future__ import annotations

import copy

from airtable import Airtable
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import add_prefix_to_dict, convert_dict_to_json_result_dict

INTEGRATION_NAME = "AirTable"


def get_unicode(value):
    return str(value)


def dict_to_flat(target_dict):
    """Receives nested dictionary and returns it as a flat dictionary.
    :param target_dict: {dict}
    :return: Flat dict : {dict}
    """
    target_dict = copy.deepcopy(target_dict)

    def expand(raw_key, raw_value):
        key = raw_key
        value = raw_value
        """
        :param key: {string}
        :param value: {string}
        :return: Recursive function.
        """
        if value is None:
            return [(get_unicode(key), "")]
        if isinstance(value, dict):
            # Handle dict type value
            return [
                (
                    f"{get_unicode(key)}_{get_unicode(sub_key)}",
                    get_unicode(sub_value),
                )
                for sub_key, sub_value in dict_to_flat(value).items()
            ]
        if isinstance(value, list):
            # Handle list type value
            count = 1
            l = []
            items_to_remove = []
            for value_item in value:
                if isinstance(value_item, dict):
                    # Handle nested dict in list
                    l.extend(
                        [
                            (
                                f"{get_unicode(key)}_{get_unicode(count)}_{get_unicode(sub_key)}",
                                sub_value,
                            )
                            for sub_key, sub_value in dict_to_flat(value_item).items()
                        ],
                    )
                    items_to_remove.append(value_item)
                    count += 1
                elif isinstance(value_item, list):
                    l.extend(
                        expand(get_unicode(key) + "_" + get_unicode(count), value_item),
                    )
                    count += 1
                    items_to_remove.append(value_item)

            for value_item in items_to_remove:
                value.remove(value_item)

            for value_item in value:
                l.extend([(get_unicode(key) + "_" + get_unicode(count), value_item)])
                count += 1

            return l
        return [(get_unicode(key), get_unicode(value))]

    items = [
        item
        for sub_key, sub_value in target_dict.items()
        for item in expand(sub_key, sub_value)
    ]
    return dict(items)


def main():
    siemplify = SiemplifyAction()

    api_key = siemplify.extract_configuration_param(
        provider_name=INTEGRATION_NAME,
        param_name="Api key",
    )
    base_id = siemplify.parameters["Base id"]
    table_name = siemplify.parameters["Table name"]
    field_name = str(siemplify.parameters["Field name"])
    entity_field = str(siemplify.parameters.get("Entity Field"))
    max_records_str = str(siemplify.parameters["Max records"])
    enrichment_prefix = siemplify.parameters.get("Enrichment Prefix", "")

    max_records = 5

    try:
        max_records = int(max_records_str)
    except ValueError:
        print(max_records_str + " is not an int!")

    airtable = Airtable(base_id, table_name, api_key)

    result_json = {}
    successful_entities = []
    failed_entities = []
    for entity in siemplify.target_entities:
        try:
            if entity_field:
                field_value = entity.additional_properties.get(entity_field)
                if not field_value:
                    raise Exception(
                        f'"{field_value}" not found in enrichment of "{entity.identifier}"',
                    )
            else:
                field_value = entity.identifier

            results = airtable.search(
                field_name,
                field_value.strip(),
                maxRecords=max_records,
            )
            if not results:
                results = airtable.search(
                    field_name,
                    field_value.strip().lower(),
                    maxRecords=max_records,
                )
        except Exception as e:
            failed_entities.append({"identifier": entity.identifier, "error": str(e)})
            continue

        if results:
            results = results[0]  # What should we do if we have more than one row?
            result_json[entity.identifier] = results
            entity.additional_properties.update(
                add_prefix_to_dict(dict_to_flat(results), enrichment_prefix),
            )
            successful_entities.append(entity)

    if successful_entities:
        siemplify.update_entities(successful_entities)

    result_value = len(successful_entities)
    output_message = f"Found results for {result_value} entities"

    if failed_entities:
        output_message += (
            "\n" + f"Failed for {len(failed_entities)} entities. See JSON for details"
        )
        siemplify.result.add_json("Errors", failed_entities)

    if result_json:
        siemplify.result.add_result_json(convert_dict_to_json_result_dict(result_json))

    siemplify.end(output_message, result_value)


if __name__ == "__main__":
    main()
