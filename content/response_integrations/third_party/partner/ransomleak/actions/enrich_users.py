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
from TIPCommon.types import SingleJson

from ..core.constants import ENRICH_USERS_SCRIPT_NAME, SUMMARY_FIELDS
from ..core.exceptions import RansomLeakAuthError
from ..core.ransomleak_manager import is_email
from ..core.utils import (
    build_manager,
    enrichment_properties,
    lookup_user_summary,
    map_concurrently,
    section,
    user_entities,
)


def _insight_html(summary: SingleJson) -> str:
    body = "".join(
        f"<tr><td style='opacity:.65;padding-right:12px'>{html.escape(label)}</td>"
        f"<td>{html.escape(str(summary[key]))}</td></tr>"
        for key, label in SUMMARY_FIELDS
        if summary.get(key) not in (None, "")
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

    json_results: SingleJson = {}
    enriched: list[Any] = []
    not_found: list[str] = []
    unsupported: list[str] = []
    failed: list[str] = []
    status = EXECUTION_STATE_COMPLETED

    try:
        manager = build_manager(siemplify)
        entities: dict[str, list[Any]] = {}
        for entity in user_entities(siemplify):
            identifier = entity.identifier.strip()
            if is_email(identifier):
                # Case variants of one address share a single lookup.
                entities.setdefault(identifier.lower(), []).append(entity)
            else:
                unsupported.append(identifier)
        if entities:
            # Fail fast on a bad key instead of fanning out N failing lookups.
            manager.test_connectivity()
        lookups = map_concurrently(lambda email: lookup_user_summary(manager, email), list(entities))
        for key, summary, error in lookups:
            identifier = entities[key][0].identifier.strip()  # first-seen spelling, for messages/results
            if isinstance(error, RansomLeakAuthError):
                raise error
            if error is not None:
                siemplify.LOGGER.error(f"Failed to enrich {identifier}: {error}")
                failed.append(identifier)
                continue
            if summary is None:
                not_found.append(identifier)
                continue
            json_results[identifier] = summary
            for entity in entities[key]:
                entity.additional_properties.update(enrichment_properties(summary))
                entity.is_enriched = True
                if create_insight:
                    siemplify.add_entity_insight(entity, _insight_html(summary))
                enriched.append(entity)

        if enriched:
            siemplify.update_entities(enriched)
            siemplify.result.add_result_json(convert_dict_to_json_result_dict(json_results))
            output_message = "Successfully enriched the following users using RansomLeak:\n" + "\n".join(
                e.identifier for e in enriched
            )
        else:
            output_message = "None of the provided users were enriched."
        output_message += section("The following users were not found in RansomLeak", not_found)
        output_message += section(
            "The following entities were skipped because their identifier is not an email address", unsupported
        )
        output_message += section("Action wasn't able to enrich the following users", failed)
        result_value = bool(enriched)
    except Exception as error:
        siemplify.LOGGER.exception(f'Error executing action "Enrich Users". Reason: {error}')
        output_message = f'Error executing action "Enrich Users". Reason: {error}'
        result_value = False
        status = EXECUTION_STATE_FAILED

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
