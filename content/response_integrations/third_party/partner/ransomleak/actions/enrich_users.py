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

from typing import TYPE_CHECKING, NoReturn

from TIPCommon.base.action import EntityInsight
from TIPCommon.extraction import extract_action_param
from TIPCommon.transformation import convert_dict_to_json_result_dict

from ..core.base_action import BaseAction
from ..core.constants import (
    ENRICH_USERS_ACTION_NAME,
    ENRICH_USERS_SCRIPT_NAME,
    INTEGRATION_NAME,
)
from ..core.exceptions import RansomLeakAuthError
from ..core.utils import (
    enrichment_properties,
    entity_identifier,
    insight_html,
    is_email,
    lookup_user_summary,
    map_concurrently,
    section,
    user_entities,
)

if TYPE_CHECKING:
    from soar_sdk.SiemplifyDataModel import DomainEntityInfo
    from TIPCommon.types import SingleJson


class EnrichUsersAction(BaseAction):
    """Enrich USER entities with RansomLeak training status and Human Risk Score."""

    def __init__(self) -> None:
        super().__init__(ENRICH_USERS_SCRIPT_NAME, ENRICH_USERS_ACTION_NAME)

    def _extract_action_parameters(self) -> None:
        create_insight: bool = extract_action_param(
            self.soar_action,
            param_name="Create Insight",
            default_value=False,
            input_type=bool,
            print_value=True,
        )
        self.params.create_insight = create_insight

    def _group_entities_by_email(self) -> tuple[dict[str, list[DomainEntityInfo]], list[str]]:
        """Group USER entities by lower-cased email so case variants share one lookup.

        Returns:
            (entities by lower-cased email, identifiers that are not email addresses).

        """
        entities: dict[str, list[DomainEntityInfo]] = {}
        unsupported: list[str] = []
        for entity in user_entities(self.soar_action):
            identifier = entity_identifier(entity)
            if is_email(identifier):
                entities.setdefault(identifier.lower(), []).append(entity)
            else:
                unsupported.append(identifier)
        return entities, unsupported

    def _enrich(self, entities: list[DomainEntityInfo], summary: SingleJson) -> None:
        properties = enrichment_properties(summary)
        for entity in entities:
            entity.additional_properties.update(properties)
            entity.is_enriched = True
            if self.params.create_insight:
                self.entity_insights.append(
                    EntityInsight(
                        entity=entity,
                        message=insight_html(summary),
                        triggered_by=INTEGRATION_NAME,
                    ),
                )

    def _perform_action(self, _: object = None) -> None:
        entities, unsupported = self._group_entities_by_email()
        if entities:
            # Fail fast on a bad key instead of fanning out N failing lookups.
            self.api_client.test_connectivity()

        json_results: SingleJson = {}
        enriched: list[DomainEntityInfo] = []
        not_found: list[str] = []
        failed: list[str] = []
        lookups = map_concurrently(
            lambda email: lookup_user_summary(self.api_client, email),
            list(entities),
        )
        for key, summary, error in lookups:
            identifier = entity_identifier(entities[key][0])  # first-seen spelling, for messages/results
            if isinstance(error, RansomLeakAuthError):
                raise error
            if error is not None:
                self.logger.error(f"Failed to enrich {identifier}: {error}")
                failed.append(identifier)
                continue
            if summary is None:
                not_found.append(identifier)
                continue
            json_results[identifier] = summary
            self._enrich(entities[key], summary)
            enriched.extend(entities[key])

        if enriched:
            self.soar_action.update_entities(enriched)
            self.json_results = convert_dict_to_json_result_dict(json_results)
            self.output_message = "Successfully enriched the following users using RansomLeak:\n" + "\n".join(
                entity_identifier(e) for e in enriched
            )
        else:
            self.output_message = "None of the provided users were enriched."
        self.output_message += section(
            "The following users were not found in RansomLeak",
            not_found,
        )
        self.output_message += section(
            "The following entities were skipped because their identifier is not an email address",
            unsupported,
        )
        self.output_message += section(
            "Action wasn't able to enrich the following users",
            failed,
        )
        self.result_value = bool(enriched)


def main() -> NoReturn:
    EnrichUsersAction().run()


if __name__ == "__main__":
    main()
