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

import json

from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

from ..core.ToolsCommon import parse_raw_message

# CONSTS:
ENTITY_IDENTIFIER_FIELD_NAME = "Entity"
JSON_DATA_FIELD_NAME = "EntityResult"
MULTIPLE_VALUES = "MULTIPLE VALUES FOUND"
MISSING_VAL = "NotFound"
NOT_SIMPLE_VAL = "Value is a dict"
NOT_FOR_TABLE = "NO_TABLE"


def GetIdentifiersAsString(target_entities):
    entitiesIdentifiers = []
    for entity in target_entities:
        entitiesIdentifiers.append(entity.identifier)
    return ", ".join(entitiesIdentifiers)


def GetEntityByString(identifier, entities):
    for ent in entities:
        if identifier.lower() == ent.identifier.lower():
            return ent
    return None


def process_trios(trio_list, ph_separator):
    bad_json = []
    insight_data = []
    for trio in trio_list:
        if trio.get("title"):  # We expect some values here
            data_obj = {}
            data_obj["title"] = trio.get("title")
            try:
                data_obj["fields"] = process_fields_string(
                    trio.get("fields"),
                    ph_separator,
                )
            except Exception as e:
                raise Exception(f"Syntax error. Error message is: {e}")
            try:
                data_obj["json"] = json.loads(trio.get("json"))
            except:
                bad_json.append(data_obj)
                continue
            insight_data.append(data_obj)

    return insight_data, bad_json


def process_fields_string(field_string, ph_separator):
    """Gets a string of the format: "Count:path1.path2.length,RISK:path3.path4.risk_score"
    and breaks it into list of objects: {"display": STRING, "key_path": STRING(path1.path2.path3)}

    Key characters: "," and ":". ":" marks the separation between display and path where "," marks separation between fields
    """
    if not field_string:
        return []

    fields_data = []
    # raise Exception(json.dumps(field_string))
    # field_string = field_string.replace(u"\n", u",")
    for field_rep in field_string.split(ph_separator):
        if field_rep.strip():  # Ignore empty
            temp = field_rep.strip().split(":")
            display = temp[0]
            if len(temp) == 1:
                key_path = temp[0]  # .split(".")
                fields_data.append({"display": NOT_FOR_TABLE, "key_path": key_path})
                continue
                # raise Exception("Field definition missing ':'. Field: {}".format(field_rep))
            # elif len(temp) != 2:
            # raise Exception("General issue with the formating of the field: {}".format(json.dumps(field_rep)))
            key_path = ":".join(temp[1:])  # .split(".")
            fields_data.append(
                {"display": display.strip(), "key_path": key_path},
            )  # [x.strip() for x in key_path]})
    return fields_data


def extract_json_based_on_entity(entity, json):
    for item in json:  # Assuming regular list format for enrichment actions
        if item[ENTITY_IDENTIFIER_FIELD_NAME].lower() == entity.identifier.lower():
            return item[JSON_DATA_FIELD_NAME]
    return None


def find_key_path_in_json(key_path, json):
    """Finds the relevant key_path in a json object.
    If list encountered, if its of len 1, its value is used. Otherwise, it exits with default value (MULTIPLE VALUES FOUND)
    """
    return find_key_path_recursive(key_path, json)


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
            return NOT_SIMPLE_VAL
        if isinstance(current_json, list):
            return ",".join(current_json)

        return f"{current_json}"  # Found val, return it. Format to make everything into string


@output_handler
def main():
    siemplify = SiemplifyAction()

    added_insights = []

    input_trios = []

    for i in range(1, 8):
        input_trios.append(
            {
                "title": siemplify.parameters.get(f"Title{i}"),
                "fields": siemplify.parameters.get(f"Fields{i}"),
                "json": siemplify.parameters.get(f"JSON{i}"),
            },
        )
    ph_separator = siemplify.parameters.get("Placeholder Separator")

    processed_trios, bad_trios = process_trios(input_trios, ph_separator)

    for ent in siemplify.target_entities:
        insight_message_list = []
        insight_message = ""
        for trio in processed_trios:
            trio_message_list = []
            not_for_tables = []
            json = extract_json_based_on_entity(ent, trio["json"])
            if json:
                for item in trio.get("fields", []):
                    display = item["display"]
                    key_path = item["key_path"]

                    val = parse_raw_message(
                        json,
                        key_path,
                    )  # find_key_path_in_json(key_path, json)
                    new_item = {"display": display, "value": val}
                    if display == NOT_FOR_TABLE:
                        not_for_tables.append(new_item)
                    else:
                        trio_message_list.append(new_item)

                rows_list = [
                    """<td><strong>{display}</strong></td><td>{value}</td></tr>""".format(
                        **trio_message_item,
                    )
                    for trio_message_item in trio_message_list
                ]
                rows = "".join(rows_list)

                trio_message = f"""<table border="1" width="290"><tbody><tr>{rows}<tr></tbody></table>"""

                title_message_list = []
                not_for_tables_message = []
                if not_for_tables:
                    not_for_tables_message = "<br>".join(
                        [x["value"] for x in not_for_tables],
                    )
                    title_message_list.append(not_for_tables_message)
                if trio_message:
                    title_message_list.append(trio_message)

                title_message = "<br>".join(
                    [x for x in [trio_message, not_for_tables_message] if x],
                )
                insight_message_list.append(title_message)
                siemplify.add_entity_insight(
                    ent,
                    title_message,
                    triggered_by=trio["title"],
                )
            else:
                insight_message_list.append(
                    """<p><span style="text-decoration: underline;">{}</span>:</p>Missing data in JSON for entity""".format(
                        trio.get("title", "MISSING TITLE"),
                    ),
                )

        if insight_message_list:
            insight_message = "<br><br>".join(insight_message_list)

        # if bad_trios:
        #     insight_message += u"<br><br>"
        #     insight_message += u"<br><br>".join([u"""<p><span style="text-decoration: underline;">{}</span>:</p>JSON Completly missing or badly formatted""".format(
        #             trio.get('title')) for trio in bad_trios])
        # raise Exception(insight_message)
        # siemplify.add_entity_insight(ent, insight_message)
        added_insights.append(ent)

    output_message = "Insight added to following entities: {}".format(
        ",".join([x.identifier for x in added_insights]),
    )

    siemplify.end(output_message, "true")


if __name__ == "__main__":
    main()
