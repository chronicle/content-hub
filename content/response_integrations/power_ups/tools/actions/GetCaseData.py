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

import base64
import json
import re
from typing import TYPE_CHECKING, Any

import requests
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from TIPCommon.rest.soar_api import get_all_case_overview_details, get_case_insights
from TIPCommon.utils import get_sdk_api_uri

if TYPE_CHECKING:
    from collections.abc import Iterable

# language=regexp
INSIGHT_CONTENT_RE = r"<%\s(.*?)\s%>$"
ACTION_NAME = "Get Case Data"
SENTINEL = object()


def lower(in_str: str) -> str:
    return f"{in_str[:1].lower()}{in_str[1:]}" if in_str else ""


def lowercase(x: Any) -> Any:
    if isinstance(x, list):
        return [lowercase(v) for v in x]

    if isinstance(x, dict):
        return {lower(k): lowercase(v) for k, v in x.items()}

    return x


def is_insight_content(content: str) -> bool:
    return content.startswith("<%") and content.endswith("%>")


def get_insight_content(
    siemplify: SiemplifyAction,
    insight: dict[str, Any],
) -> dict | list:
    content_uri = re.match(INSIGHT_CONTENT_RE, insight["content"])
    if content_uri is None:
        siemplify.LOGGER.info(
            f"Not passed insight regex to retrieve data: {insight['content']}"
        )
        return insight

    content_uri = content_uri.group(1)

    url = f"{get_sdk_api_uri(siemplify)}/{content_uri}"
    insight_content_res = siemplify.session.get(
        url
    )
    insight_content_res.raise_for_status()

    return lowercase(
        json.loads(base64.b64decode(insight_content_res.json().get("blob", "e30K"))),
    )


def filter_json_by_fields(
    json_: dict[str, Any] | list[dict[str, Any]],
    filter_fields: Iterable[str],
    nested_fields_delimiter: str | None = None,
) -> tuple[dict[str, Any] | list[dict[str, Any]], list[str]]:
    if not filter_fields:
        return json_, []

    result = {}
    not_found_fields = []
    for field in filter_fields:
        current = json_
        value = None
        keys = [field]
        if nested_fields_delimiter is not None:
            keys = field.split(nested_fields_delimiter)

        for key in keys:
            if value is SENTINEL:
                break

            value = SENTINEL
            if isinstance(current, list) and key.isdigit():
                index = int(key)
                value = SENTINEL
                if index < len(current):
                    value = current[index]
                    current = current[index]

            elif isinstance(current, dict):
                value = current.get(key, SENTINEL)
                if value is not SENTINEL:
                    current = current[key]

        if value is not SENTINEL:
            result[field] = value

        else:
            not_found_fields.append(field)

    return result, not_found_fields


@output_handler
def main() -> None:
    siemplify = SiemplifyAction()
    siemplify.script_name = ACTION_NAME
    siemplify.LOGGER.info("---------------- Main - Param Init ----------------")
    case_id = siemplify.extract_action_param(
        param_name="Case Id",
        default_value=siemplify.case_id,
        print_value=True,
    )
    fields_to_return = siemplify.extract_action_param(
        param_name="Fields to Return",
        print_value=True,
    )
    nested_keys_delimiter = siemplify.extract_action_param(
        param_name="Nested Keys Delimiter",
        print_value=True,
    )

    siemplify.LOGGER.info("---------------- Main - Started ----------------")
    result_value = True
    action_status = EXECUTION_STATE_COMPLETED
    output_message = f"Finished executing {ACTION_NAME} successfully"

    try:
        if nested_keys_delimiter == ",":
            raise ValueError(
                '"Nested Keys Delimiter" cannot be a comma as this value is '
                'saved as the delimiter for the "Fields to Return" parameter',
            )

        fields_list = (
            {s.strip() for s in fields_to_return.split(",") if s}
            if fields_to_return
            else set()
        )

        siemplify.LOGGER.info("Fetching case data")
        case_data = get_all_case_overview_details(siemplify, case_id)

        case_json = case_data.to_json()
        case_json["alerts"] = case_json.pop("alertCards", [])
        result, not_found_fields = filter_json_by_fields(
            json_=case_json,
            filter_fields=fields_list,
            nested_fields_delimiter=nested_keys_delimiter,
        )
        siemplify.LOGGER.info("Filtering by fields")

        if not result:
            raise ValueError("None of the provided fields were found in the response.")

        insights = get_case_insights(siemplify, case_id)
        if len(insights) > 0:
            siemplify.LOGGER.info("Fetching insights contents")
            parsed_insights = []
            for insight in insights:
                content_to_add = insight
                if is_insight_content(insight["content"]):
                    try:
                        content_to_add = get_insight_content(siemplify, insight)

                    except (requests.exceptions.HTTPError, json.JSONDecodeError) as e:
                        siemplify.LOGGER.error(
                            "Failed to get the insight content for the insight: "
                            f'{insight.get("title")}'
                        )
                        siemplify.LOGGER.error(e)

                parsed_insights.append(content_to_add)

            result["insights"] = parsed_insights

        if not_found_fields:
            output_message += (
                "\nThe following fields were not found: "
                f"""{", ".join(f'"{s}"' for s in not_found_fields)}"""
            )

        siemplify.result.add_result_json(result)

    except Exception as e:
        output_message = f"Error executing {ACTION_NAME}. Reason: {e}"
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
        result_value = False
        action_status = EXECUTION_STATE_FAILED

    siemplify.LOGGER.info("---------------- Main - Finished ----------------")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.LOGGER.info(f"Result: {result_value}")
    siemplify.LOGGER.info(f"Execution Status: {action_status}")
    siemplify.end(output_message, result_value, action_status)


if __name__ == "__main__":
    main()
