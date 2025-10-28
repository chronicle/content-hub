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
from typing import TYPE_CHECKING, Any

from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

if TYPE_CHECKING:
    from collections.abc import Iterable

NOT_FOUND = object()


def filter_json_by_fields(
    json_: dict[str, Any] | list[dict[str, Any]],
    filter_fields: Iterable[str],
    siemplify: Any,
    nested_fields_delimiter: str | None = None,
) -> tuple[dict[str, Any] | list[dict[str, Any]], list[str]]:

    siemplify.LOGGER.info(f"Filter fields: {filter_fields}")

    if not filter_fields:
        return json_, []

    result = {}
    not_found_fields = []

    for field in filter_fields:
        try:
            siemplify.LOGGER.info(f"Processing field: {field}")
            keys = [field]
            if nested_fields_delimiter and nested_fields_delimiter in field:
                keys = field.split(nested_fields_delimiter)

            current_value = json_
            found = True
            for key in keys:
                siemplify.LOGGER.info(f"Accessing key: {key}")
                if isinstance(current_value, dict):
                    current_value = current_value.get(key, NOT_FOUND)
                elif isinstance(current_value, list) and key.isdigit():
                    index = int(key)
                    if index < len(current_value):
                        current_value = current_value[index]
                    else:
                        siemplify.LOGGER.info(
                            f"Index {index} is out of bounds for list."
                        )
                        current_value = NOT_FOUND
                else:
                    current_value = NOT_FOUND

                if current_value is NOT_FOUND:
                    found = False
                    break

            if found:
                result[field] = current_value
            else:
                not_found_fields.append(field)

        except Exception as e:
            siemplify.LOGGER.error(
                f"An error occurred while processing field '{field}': {e}"
            )
            siemplify.LOGGER.exception(e)
            not_found_fields.append(field)

    return result, not_found_fields


@output_handler
def main():
    try:
        siemplify = SiemplifyAction(get_source_file=True)
    except TypeError:
        siemplify = SiemplifyAction()

    case_ids = siemplify.parameters.get("Case ID", "")
    alert_ids = siemplify.parameters.get("Alert ID", "")
    fields_to_return = siemplify.parameters.get("Fields To Return", "")
    nested_keys_delimiter = "."

    all_alerts = []
    output_message = ""

    if not case_ids:

        if alert_ids:
            raise Exception("Alert ID cannot be provided without Case ID.")

        if siemplify.current_alert and siemplify.current_alert.entities:
            try:
                case_data = json.loads(
                    siemplify.current_alert.entities[0].additional_properties[
                        "SourceFileContent"
                    ],
                )
                all_alerts.append(case_data)
            except (json.JSONDecodeError, KeyError) as e:
                siemplify.LOGGER.error(
                    f"Error parsing SourceFileContent from current alert: {e}"
                )
                siemplify.LOGGER.exception(e)
        else:
            siemplify.LOGGER.info(
                "No current alert or entities found, returning empty result."
            )
    else:
        siemplify.LOGGER.info(f"Case IDs provided: {case_ids}")
        case_id_list = [c.strip() for c in case_ids.split(",") if c.strip()]
        alert_id_list = [a.strip() for a in alert_ids.split(",") if a.strip()]

        for case_id in case_id_list:
            siemplify.LOGGER.info(
                f"Attempting to fetch case object for case ID: {case_id}"
            )
            case_obj = siemplify._get_case_by_id(case_id)
            if case_obj:
                alerts_in_case = case_obj.get("cyber_alerts", [])
                if alerts_in_case:
                    for alert in alerts_in_case:
                        alert_id = alert.get("additional_properties", {}).get(
                            "Alert_Id"
                        )
                        if not alert_id_list or str(alert_id) in alert_id_list:
                            all_alerts.append(alert)
                else:
                    siemplify.LOGGER.info(
                        f"No alerts found within case object for case ID: {case_id}"
                    )
            else:
                siemplify.LOGGER.info(f"Case object not found for case ID: {case_id}")

    # Apply field filtering
    if fields_to_return:
        fields = [f.strip() for f in fields_to_return.split(",") if f.strip()]
        filtered_alerts = []
        not_found_fields = set()

        for alert_data in all_alerts:
            filtered_alert, not_found = filter_json_by_fields(
                json_=alert_data,
                filter_fields=fields,
                siemplify=siemplify,
                nested_fields_delimiter=nested_keys_delimiter,
            )
            if filtered_alert:
                filtered_alerts.append(filtered_alert)
            not_found_fields.update(not_found)

        if not_found_fields:
            not_found_fields_str = ", ".join(f'"{s}"' for s in not_found_fields)
            output_message += (
                f"The following fields were not found: {not_found_fields_str}"
            )

        all_alerts = filtered_alerts

    # Determine output format
    if len(all_alerts) == 1:
        result_data = all_alerts[0]
    else:
        result_data = all_alerts

    siemplify.result.add_result_json(result_data)
    siemplify.end(output_message, json.dumps(result_data))


if __name__ == "__main__":
    main()
