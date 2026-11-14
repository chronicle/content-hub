# Copyright 2026 RansomLeak
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

import html
from typing import Any

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from TIPCommon.extraction import extract_action_param
from TIPCommon.transformation import convert_dict_to_json_result_dict

from ..core.constants import ENRICH_USERS_SCRIPT_NAME
from ..core.exceptions import RansomLeakAuthError
from ..core.ransomleak_manager import is_email
from ..core.utils import build_manager, enrichment_properties, user_entities, user_summary


def _insight_html(summary: dict[str, Any]) -> str:
    rows = [
        ("Human Risk Score", summary.get("risk_score")),
        ("Risk level", summary.get("risk_level")),
        ("Exercises completed", summary.get("exercises_completed")),
        ("Learning time (min)", summary.get("learning_time_minutes")),
        ("Campaigns completed", summary.get("campaigns_completed")),
        ("Campaigns in progress", summary.get("campaigns_in_progress")),
        ("Campaigns overdue", summary.get("campaigns_overdue")),
        ("Average quiz score", summary.get("average_quiz_score")),
        ("Last completed", summary.get("last_completed_exercise")),
        ("Last completed at", summary.get("last_completed_at")),
    ]
    body = "".join(
        f"<tr><td style='opacity:.65;padding-right:12px'>{html.escape(label)}</td>"
        f"<td>{html.escape(str(value))}</td></tr>"
        for label, value in rows
        if value not in (None, "")
    )
    return f"<b>RansomLeak training status</b><table>{body}</table>"


@output_handler
def main() -> None:
    """Enrich USER entities with RansomLeak training status and Human Risk Score."""
    siemplify = SiemplifyAction()
    siemplify.script_name = ENRICH_USERS_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")
    create_insight = extract_action_param(
        siemplify,
        param_name="Create Insight",
        default_value=False,
        input_type=bool,
        print_value=True,
    )
    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    json_results: dict[str, Any] = {}
    enriched: list[Any] = []
    not_found: list[str] = []
    unsupported: list[str] = []
    failed: list[str] = []
    status = EXECUTION_STATE_COMPLETED

    try:
        manager = build_manager(siemplify)
        for entity in user_entities(siemplify):
            identifier = entity.identifier.strip()
            if not is_email(identifier):
                unsupported.append(identifier)
                continue
            try:
                user = manager.get_user_by_email(identifier)
                if user is None:
                    not_found.append(identifier)
                    continue
                summary = user_summary(manager, user)
                entity.additional_properties.update(enrichment_properties(summary))
                entity.is_enriched = True
                if create_insight:
                    siemplify.add_entity_insight(entity, _insight_html(summary))
                json_results[identifier] = summary
                enriched.append(entity)
            except RansomLeakAuthError:
                raise
            except Exception as error:
                siemplify.LOGGER.error(f"Failed to enrich {identifier}: {error}")
                siemplify.LOGGER.exception(error)
                failed.append(identifier)

        if enriched:
            siemplify.update_entities(enriched)
            siemplify.result.add_result_json(convert_dict_to_json_result_dict(json_results))
            output_message = "Successfully enriched the following users using RansomLeak:\n" + "\n".join(
                e.identifier for e in enriched
            )
        else:
            output_message = "None of the provided users were enriched."
        if not_found:
            output_message += "\nThe following users were not found in RansomLeak:\n" + "\n".join(not_found)
        if unsupported:
            output_message += (
                "\nThe following entities were skipped because their identifier is not an email address:\n"
                + "\n".join(unsupported)
            )
        if failed:
            output_message += "\nAction wasn't able to enrich the following users:\n" + "\n".join(failed)
        result_value = bool(enriched)
    except Exception as error:
        siemplify.LOGGER.error(f'Error executing action "Enrich Users". Reason: {error}')
        siemplify.LOGGER.exception(error)
        output_message = f'Error executing action "Enrich Users". Reason: {error}'
        result_value = False
        status = EXECUTION_STATE_FAILED

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
