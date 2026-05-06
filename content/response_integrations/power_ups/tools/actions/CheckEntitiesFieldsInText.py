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
import re

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import convert_dict_to_json_result_dict, output_handler


def get_entity_object_by_identifier(siemplify, identifier):
    for entity in siemplify.target_entities:
        if identifier.lower() == entity.identifier.lower():
            return entity
    return None


@output_handler
def main():
    siemplify = SiemplifyAction()

    status = EXECUTION_STATE_COMPLETED
    output_message = "output message :"
    result_value = False
    failed_entities = []
    successfull_entities = []
    json_result = {}

    fields_json = json.loads(siemplify.parameters.get("FieldsInput"))
    search_data_json = json.loads(siemplify.parameters.get("SearchInData"))
    enrich_key = siemplify.parameters.get("ShouldEnrichEntity", "")
    is_case_sensitive = siemplify.parameters.get("IsCaseSensitive").lower() == "true"

    for entity in siemplify.target_entities:
        try:
            entity_fields_json = copy.deepcopy(fields_json)
            for item in entity_fields_json:
                item_results = []
                # for event in siemplify.current_alert.security_events:
                if item.get("RegexForFieldName"):
                    item_results.extend({
                                    "key": key,
                                    "val": entity.additional_properties.get(key),
                                } for key in entity.additional_properties if re.search(item.get("RegexForFieldName"), key))
                else:
                    item_results.append(
                        {
                            "key": item["FieldName"],
                            "val": entity.additional_properties.get(
                                item["FieldName"],
                            ),
                        },
                    )

                item_results = [x for x in item_results if x["val"]]

                if item.get("RegexForFieldValue"):
                    values_post_regex = []
                    for val in item_results:
                        post_regex_val = re.findall(
                            item.get("RegexForFieldValue"),
                            val["val"],
                        )
                        if isinstance(post_regex_val, list):
                            values_post_regex.append(
                                [{"key": item["FieldName"], "val": x} for x in post_regex_val],
                            )
                        else:
                            values_post_regex.append(
                                [{"key": item["FieldName"], "val": post_regex_val}],
                            )
                        # values_post_regex.append(post_regex_val)
                    item["ResultsToSearch"] = {"val_to_search": values_post_regex}
                    # print(values_post_regex)
                else:
                    item["ResultsToSearch"] = {"val_to_search": [item_results]}
                item["ResultsToSearch"]["found_results"] = []
                item["ResultsToSearch"]["num_of_results"] = 0

                # Prepare values to search in:
                regex_for_search_field = item.get("RegEx")
                if not regex_for_search_field:
                    regex_for_search_field = ".*"
                for item in search_data_json:
                    search_string = re.findall(regex_for_search_field, item["Data"])
                    if isinstance(search_string, list):
                        item["search_string"] = " ".join(search_string)
                    else:
                        item["search_string"] = search_string
            json_result[entity.identifier] = entity_fields_json
        except Exception:
            failed_entities.append(entity.identifier)
            raise

    # # Prepare values to search in:
    # regex_for_search_field = item.get("RegEx")
    # if not regex_for_search_field:
    #     regex_for_search_field = ".*"
    # for item in search_data_json:
    #     search_string = re.findall(regex_for_search_field, item["Data"])
    #     if isinstance(search_string, list):
    #         item["search_string"] = " ".join(search_string)
    #     else:
    #         item["search_string"] = search_string

    # Find matches!!
    for entity_id, entity_data in json_result.items():
        for item in entity_data:
            for vals in item.get("ResultsToSearch", []).get("val_to_search", []):
                for search_in_item in search_data_json:
                    for val in vals:
                        if (is_case_sensitive and val["val"] in search_in_item.get("search_string")) or (
                            not is_case_sensitive
                            and val["val"].lower() in search_in_item.get("search_string").lower()
                        ):
                            item.get("ResultsToSearch", [])["found_results"].append(
                                {
                                    "to_search": val,
                                    "searched_in": search_in_item.get(
                                        "search_string",
                                    ),
                                },
                            )
                            item.get("ResultsToSearch", [])["num_of_results"] += 1

                            ent = get_entity_object_by_identifier(
                                siemplify,
                                entity_id,
                            )
                            successfull_entities.append(ent)
                            if enrich_key:
                                ent.additional_properties[enrich_key] = True

    if enrich_key:
        siemplify.update_entities(successfull_entities)

    if json_result:
        siemplify.result.add_result_json(
            convert_dict_to_json_result_dict(json_result),
        )

    if successfull_entities:
        unique_entity_identifiers = list(
            {x.identifier for x in successfull_entities},
        )
        output_message += "\n Successfully processed entities:\n   {}".format(
            "\n   ".join(unique_entity_identifiers),
        )
    else:
        output_message += "\n No entities where processed."

    result_value = len(successfull_entities)

    if failed_entities:
        output_message += "\n Failed processing entities:\n   {}".format(
            "\n   ".join(failed_entities),
        )
        status = EXECUTION_STATE_FAILED

    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
