# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import annotations

import copy
import json

from jsonpath_ng.ext import parse
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import add_prefix_to_dict, output_handler

# CONSTS
MULTIPLE_VALUES = "MULTIPLE VALUES FOUND"
MISSING_VAL = "NotFound"
NOT_SIMPLE_VAL = "NOT A SIMPLE VALUE. ONLY SUPPORTS STRING"


def get_alert_entities(siemplify):
    return [entity for alert in siemplify.case.alerts for entity in alert.entities]


@output_handler
def main():
    siemplify = SiemplifyAction()

    json_data = siemplify.parameters.get("Enrichment JSON")
    enrichment_json = json.loads(json_data)  # we assume to have a list here
    key_path_raw = siemplify.parameters.get("Identifier KeyPath")
    separator = siemplify.parameters.get("Separator", ".")

    list_of_key_lists = [key_path.split(separator) for key_path in key_path_raw.split("\n")]
    prefix = siemplify.parameters.get("PrefixForEnrichment")
    enrichment_jsonpath = siemplify.parameters.get("Enrichment JSONPath", None)

    if enrichment_jsonpath:
        json_expression = parse(enrichment_jsonpath)
    updated_entities = []

    target_entities = []
    target_entities = list(siemplify.target_entities)

    for entity in target_entities:
        for curr_enrich_json in enrichment_json:
            json_identifier = None
            for key_list in list_of_key_lists:
                json_identifier = find_key_path_in_json(key_list, curr_enrich_json)
                if json_identifier:
                    if enrichment_jsonpath:
                        enrich_dict = {}
                        match = json_expression.find(curr_enrich_json)
                        for m in match:
                            enrich_dict[str(m.path)] = m.value.encode("utf-8")
                        if prefix:
                            entity.additional_properties.update(
                                add_prefix_to_dict(
                                    dict_to_flat(enrich_dict),
                                    prefix,
                                ),
                            )
                        else:
                            entity.additional_properties.update(
                                dict_to_flat(enrich_dict),
                            )
                        updated_entities.append(entity)
                        break

                    if prefix:
                        entity.additional_properties.update(
                            add_prefix_to_dict(
                                dict_to_flat(curr_enrich_json),
                                prefix,
                            ),
                        )
                    else:
                        entity.additional_properties.update(
                            dict_to_flat(curr_enrich_json),
                        )
                    updated_entities.append(entity)
                    break
    count_updated_entities = len(updated_entities)

    if count_updated_entities > 0:
        siemplify.update_entities(updated_entities)

    siemplify.end(
        f"{count_updated_entities} entities were successfully enriched",
        count_updated_entities,
        EXECUTION_STATE_COMPLETED,
    )


def get_unicode(val):
    return str(val)


def find_key_path_in_json(key_path, json_data):
    """Finds the relevant key_path in a json object.
    If list encountered, if its of len 1, its value is used. Otherwise, it exits with default value (MULTIPLE VALUES FOUND)
    """
    return find_key_path_recursive(key_path, json_data)


def find_key_path_recursive(key_list, current_json):
    if key_list:
        if isinstance(current_json, list):
            if key_list:
                if len(current_json) == 1:
                    return find_key_path_recursive(key_list, current_json[0])
                return MULTIPLE_VALUES
            return ", ".join(current_json)
        if isinstance(current_json, dict):
            if key_list[0] in current_json:
                return find_key_path_recursive(key_list[1:], current_json[key_list[0]])
            # raise Exception("Key: {}, json: {}".format(key_list, current_json))
            return MISSING_VAL
    else:
        if isinstance(current_json, dict):
            msg = f"Not a simple value.  Unable to enrich. Key: {key_list}, json: {current_json}"
            raise Exception(
                msg,
            )
        if isinstance(current_json, list):
            return ",".join(current_json)

        return f"{current_json}"  # Found val, return it. Format to make everything into string
    return None


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
            value_list = []
            items_to_remove = []
            for value_item in value:
                if isinstance(value_item, dict):
                    value_list.extend(
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
                    value_list.extend(
                        expand(get_unicode(key) + "_" + get_unicode(count), value_item),
                    )
                    count += 1
                    items_to_remove.append(value_item)

            for value_item in items_to_remove:
                value.remove(value_item)

            for value_item in value:
                value_list.extend(
                    [(get_unicode(key) + "_" + get_unicode(count), value_item)],
                )
                count += 1

            return value_list
        return [(get_unicode(key), get_unicode(value))]

    items = [item for sub_key, sub_value in target_dict.items() for item in expand(sub_key, sub_value)]
    return dict(items)


if __name__ == "__main__":
    main()
