from __future__ import annotations

from typing import TYPE_CHECKING, Any

from TIPCommon.base.action.data_models import EntityInsight, Link
from TIPCommon.extraction import extract_action_param

from ..core import constants
from ..core.base_action import HuntbaseAction
from ..core.utils import ENTITY_LOOKUP_TYPES, entity_kind, entity_value, indicator_insight, prefixed

if TYPE_CHECKING:
    from typing import NoReturn


class EnrichEntities(HuntbaseAction):
    """Enrich IP, domain, URL, hash, hostname and user entities from Huntbase."""

    def __init__(self) -> None:
        super().__init__(constants.ENRICH_ENTITIES_SCRIPT_NAME)
        self.error_output_message = f'Error executing action "{constants.ENRICH_ENTITIES_SCRIPT_NAME}"'

    def _extract_action_parameters(self) -> None:
        self.params.create_insight = extract_action_param(
            self.soar_action,
            param_name="Create Insight",
            input_type=bool,
            default_value=True,
            print_value=True,
        )
        self.params.threshold = extract_action_param(
            self.soar_action,
            param_name="Suspicious Threshold",
            input_type=int,
            default_value=constants.DEFAULT_SUSPICIOUS_THRESHOLD,
            print_value=True,
        )
        self.params.only_known = extract_action_param(
            self.soar_action,
            param_name="Only Enrich Known Values",
            input_type=bool,
            default_value=False,
            print_value=True,
        )

    def _validate_params(self) -> None:
        if not 0 <= self.params.threshold <= 100:  # noqa: PLR2004
            msg = "Suspicious Threshold must be between 0 and 100."
            raise ValueError(msg)

    def _perform_action(self, _: object) -> None:
        entities = list(self.soar_action.target_entities)
        intel_entities = [e for e in entities if (entity_kind(e) or ("",))[0] == "intel"]
        graph_entities = [e for e in entities if (entity_kind(e) or ("",))[0] == "entity"]
        if not intel_entities and not graph_entities:
            self.output_message = (
                "No supported entities found. Huntbase enriches IP, domain, URL, hash, hostname and user entities."
            )
            self.result_value = False
            return

        enriched: list[Any] = []
        not_found: list[Any] = []
        failed: list[Any] = []
        json_results: list[dict[str, Any]] = []

        if intel_entities:
            values = [entity_value(e) for e in intel_entities]
            results = {r.input.lower(): r for r in self.manager.lookup_indicators(values)}
            for entity in intel_entities:
                result = results.get(entity_value(entity).lower())
                if result is None:
                    failed.append(entity)
                    continue
                json_results.append({
                    "Entity": entity.identifier,
                    "EntityResult": result.raw_data | {"url": result.url},
                })
                if not result.is_known and self.params.only_known:
                    not_found.append(entity)
                    continue
                details = result.enrichment()
                self._enrich(entity, details, suspicious=result.is_suspicious(self.params.threshold))
                (enriched if result.is_known else not_found).append(entity)
                if result.is_known and result.url:
                    self.links.append(Link(link=result.url, title=f"Huntbase: {entity.identifier}"))

        for entity in graph_entities:
            entity_type = ENTITY_LOOKUP_TYPES.get(entity_kind(entity)[1])
            try:
                matches = self.manager.find_entities(entity_value(entity), entity_type=entity_type)
            except Exception as error:  # noqa: BLE001
                self.logger.error(f"Entity search failed for {entity.identifier}: {error}")
                failed.append(entity)
                continue
            exact = [m for m in matches if (m.key or m.label or "").lower() == entity_value(entity).lower()]
            match = (exact or matches or [None])[0]
            json_results.append({
                "Entity": entity.identifier,
                "EntityResult": match.raw_data | {"url": match.url} if match else {"status": "unknown"},
            })
            if match is None:
                not_found.append(entity)
                continue
            self._enrich(entity, match.enrichment(), suspicious=False)
            enriched.append(entity)
            if match.url:
                self.links.append(Link(link=match.url, title=f"Huntbase: {entity.identifier}"))

        self.json_results = json_results
        if enriched or not_found:
            self.soar_action.update_entities(enriched + [e for e in not_found if e.is_enriched])
        self.output_message = self._summary(enriched, not_found, failed)
        self.result_value = bool(enriched)

    def _enrich(self, entity: Any, details: dict[str, Any], suspicious: bool) -> None:  # noqa: ANN401
        entity.additional_properties.update(prefixed(details))
        entity.is_enriched = True
        if suspicious:
            entity.is_suspicious = True
        if self.params.create_insight and details.get("status") == "known":
            self.entity_insights.append(
                EntityInsight(
                    entity=entity,
                    message=indicator_insight(entity.identifier, details),
                    triggered_by=constants.INTEGRATION_NAME,
                )
            )

    @staticmethod
    def _summary(enriched: list[Any], not_found: list[Any], failed: list[Any]) -> str:  # noqa: ANN401
        lines = []
        if enriched:
            lines.append(
                "Successfully enriched the following entities using Huntbase: "
                + ", ".join(e.identifier for e in enriched)
            )
        if not_found:
            lines.append("Huntbase has no record of: " + ", ".join(e.identifier for e in not_found))
        if failed:
            lines.append("Could not enrich: " + ", ".join(e.identifier for e in failed))
        if not enriched:
            lines.append("None of the provided entities were found in Huntbase.")
        return "\n".join(lines)


def main() -> NoReturn:
    EnrichEntities().run()


if __name__ == "__main__":
    main()
