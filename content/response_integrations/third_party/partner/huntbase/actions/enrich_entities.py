from __future__ import annotations

import dataclasses
from typing import TYPE_CHECKING

from TIPCommon.base.action.data_models import EntityInsight, Link
from TIPCommon.extraction import extract_action_param

from ..core import constants
from ..core.base_action import HuntbaseAction
from ..core.utils import ENTITY_LOOKUP_TYPES, entity_kind, entity_value, indicator_insight, prefixed

if TYPE_CHECKING:
    from typing import NoReturn

    from soar_sdk.SiemplifyDataModel import DomainEntityInfo
    from TIPCommon.types import SingleJson

MAX_THRESHOLD: int = 100


@dataclasses.dataclass(slots=True)
class _Outcome:
    """What happened to each entity in one run."""

    enriched: list[DomainEntityInfo] = dataclasses.field(default_factory=list)
    not_found: list[DomainEntityInfo] = dataclasses.field(default_factory=list)
    failed: list[DomainEntityInfo] = dataclasses.field(default_factory=list)
    json_results: list[SingleJson] = dataclasses.field(default_factory=list)


def _channel(entity: DomainEntityInfo) -> str:
    return (entity_kind(entity) or ("",))[0]


def _summary(outcome: _Outcome) -> str:
    lines: list[str] = []
    if outcome.enriched:
        lines.append(
            "Successfully enriched the following entities using Huntbase: "
            + ", ".join(e.identifier for e in outcome.enriched)
        )
    if outcome.not_found:
        lines.append("Huntbase has no record of: " + ", ".join(e.identifier for e in outcome.not_found))
    if outcome.failed:
        lines.append("Could not enrich: " + ", ".join(e.identifier for e in outcome.failed))
    if not outcome.enriched:
        lines.append("None of the provided entities were found in Huntbase.")
    return "\n".join(lines)


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
        if not 0 <= self.params.threshold <= MAX_THRESHOLD:
            msg = f"Suspicious Threshold must be between 0 and {MAX_THRESHOLD}."
            raise ValueError(msg)

    def _perform_action(self, _: object) -> None:
        entities: list[DomainEntityInfo] = list(self.soar_action.target_entities)
        intel_entities = [e for e in entities if _channel(e) == "intel"]
        graph_entities = [e for e in entities if _channel(e) == "entity"]
        if not intel_entities and not graph_entities:
            self.output_message = (
                "No supported entities found. Huntbase enriches IP, domain, URL, hash, hostname and user entities."
            )
            self.result_value = False
            return

        outcome = _Outcome()
        if intel_entities:
            self._enrich_intel_entities(intel_entities, outcome)
        self._enrich_graph_entities(graph_entities, outcome)

        self.json_results = outcome.json_results
        self.entities_to_update.extend(outcome.enriched + [e for e in outcome.not_found if e.is_enriched])
        self._send_entities_to_update()
        self.output_message = _summary(outcome)
        self.result_value = bool(outcome.enriched)

    def _enrich_intel_entities(self, entities: list[DomainEntityInfo], outcome: _Outcome) -> None:
        """IPs, domains, URLs and hashes: one batched POST /intel/lookup."""
        values = [entity_value(e) for e in entities]
        results = {r.input.lower(): r for r in self.manager.lookup_indicators(values)}
        for entity in entities:
            result = results.get(entity_value(entity).lower())
            if result is None:
                outcome.failed.append(entity)
                continue
            outcome.json_results.append({
                "Entity": entity.identifier,
                "EntityResult": result.raw_data | {"url": result.url},
            })
            if not result.is_known and self.params.only_known:
                outcome.not_found.append(entity)
                continue
            self._enrich(entity, result.enrichment(), suspicious=result.is_suspicious(self.params.threshold))
            (outcome.enriched if result.is_known else outcome.not_found).append(entity)
            if result.is_known and result.url:
                self.links.append(Link(link=result.url, title=f"Huntbase: {entity.identifier}"))

    def _enrich_graph_entities(self, entities: list[DomainEntityInfo], outcome: _Outcome) -> None:
        """Hostnames and users: GET /entities/by-value per entity; one failure does not stop the rest."""
        for entity in entities:
            entity_type = ENTITY_LOOKUP_TYPES.get(entity_kind(entity)[1])
            try:
                matches = self.manager.find_entities(entity_value(entity), entity_type=entity_type)
            except Exception as error:  # noqa: BLE001
                self.logger.error(f"Entity search failed for {entity.identifier}: {error}")
                outcome.failed.append(entity)
                continue
            exact = [m for m in matches if (m.key or m.label or "").lower() == entity_value(entity).lower()]
            match = (exact or matches or [None])[0]
            outcome.json_results.append({
                "Entity": entity.identifier,
                "EntityResult": match.raw_data | {"url": match.url} if match else {"status": "unknown"},
            })
            if match is None:
                outcome.not_found.append(entity)
                continue
            self._enrich(entity, match.enrichment(), suspicious=False)
            outcome.enriched.append(entity)
            if match.url:
                self.links.append(Link(link=match.url, title=f"Huntbase: {entity.identifier}"))

    def _enrich(self, entity: DomainEntityInfo, details: SingleJson, suspicious: bool) -> None:
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


def main() -> NoReturn:
    EnrichEntities().run()


if __name__ == "__main__":
    main()
