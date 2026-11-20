from __future__ import annotations

import json
from typing import TYPE_CHECKING

from TIPCommon.base.action.data_models import EntityInsight, ExecutionState
from TIPCommon.extraction import extract_action_param

from ..core.base_action import HoudinAction
from ..core.exceptions import HoudinAccountError, HoudinError
from ..core.houdin_constants import DEFAULT_SUSPICIOUS_THRESHOLD, ENRICH_ENTITIES_SCRIPT_NAME, INTEGRATION_NAME
from ..core.houdin_utils import (
    enrichment_fields,
    insight_content,
    is_scannable_entity,
    load_state,
    parse_scanners,
    parse_threshold,
    scan_link,
    verdict_line,
    verdict_of,
)

if TYPE_CHECKING:
    from soar_sdk.SiemplifyDataModel import DomainEntityInfo
    from TIPCommon.types import SingleJson

    from ..core.data_models import ScanLaunch

SUPPORTED_TYPES_NOTE: str = (
    "Supported entities: public IPv4 and IPv6 addresses, URLs, domains and hostnames, MD5, SHA1 and SHA256 hashes."
)
IN_PROGRESS_MESSAGE: str = "Houdin is still scanning {count}: {identifiers}"
SUCCESS_MESSAGE: str = "Enriched {count} with Houdin:\n{lines}"
NO_ENTITIES_MESSAGE: str = f"No entity was scanned. {SUPPORTED_TYPES_NOTE}"


class EnrichEntities(HoudinAction):
    """Scan every supported entity of the alert and enrich it with the MesmerAI verdict.

    The state carried between runs in additional_data: `scans` maps each scanID to
    its entity identifier, `done` lists the scanIDs already enriched, `failed` maps
    the entities Houdin refused to the reason. Every run reads the pending scans
    once and ends IN_PROGRESS while any is still running.
    """

    def __init__(self) -> None:
        super().__init__(ENRICH_ENTITIES_SCRIPT_NAME)
        self.state: SingleJson = {"scans": {}, "done": [], "failed": {}}
        # The scans that finished during this run, keyed by scanID.
        self.documents: dict[str, SingleJson] = {}

    def _extract_action_parameters(self) -> None:
        self.params.scanners = parse_scanners(
            extract_action_param(self.soar_action, param_name="Scanners", print_value=True),
        )
        self.params.force_rescan = extract_action_param(
            self.soar_action,
            param_name="Force Rescan",
            input_type=bool,
            default_value=False,
        )
        self.params.create_insight = extract_action_param(
            self.soar_action,
            param_name="Create Insight",
            input_type=bool,
            default_value=True,
        )
        self.params.threshold_raw = extract_action_param(
            self.soar_action,
            param_name="Suspicious Threshold",
            print_value=True,
        )
        self.params.state = load_state(extract_action_param(self.soar_action, param_name="additional_data"))

    def _validate_params(self) -> None:
        self.params.threshold = parse_threshold(self.params.threshold_raw, DEFAULT_SUSPICIOUS_THRESHOLD)

    def _perform_action(self, _: DomainEntityInfo | None = None) -> None:
        if self.params.state is None:
            self._launch_entity_scans()
        else:
            self.state = self.params.state

        pending: list[str] = self._pending_scans()
        if pending:
            self.documents = self.api_client.get_results(pending)
            self._enrich_completed_entities()

        still_running: list[str] = self._pending_scans()
        if still_running:
            waiting: str = ", ".join(self.state["scans"][scan_id] for scan_id in still_running)
            self.logger.info(f"Waiting on {len(still_running)} scan(s): {waiting}")
            self.execution_state = ExecutionState.IN_PROGRESS
            self.result_value = json.dumps(self.state)
            self.output_message = IN_PROGRESS_MESSAGE.format(
                count=plural(len(still_running), "entity", "entities"),
                identifiers=waiting,
            )
            return

        self._build_final_results()

    def _pending_scans(self) -> list[str]:
        return [scan_id for scan_id in self.state["scans"] if scan_id not in self.state["done"]]

    def _launch_entity_scans(self) -> None:
        """First run: one scan per scannable entity; a refused artifact is recorded and skipped.

        Raises:
            HoudinAccountError: The refusal concerns the account (key, quota), so the action fails.
        """
        for entity in self.soar_action.target_entities:
            if not is_scannable_entity(entity):
                self.logger.info(f"Skipping {entity.identifier} ({entity.entity_type}): not scannable")
                continue
            try:
                launch: ScanLaunch = self.api_client.launch_scan(
                    entity.identifier,
                    self.params.scanners,
                    self.params.force_rescan,
                )
            except HoudinAccountError:
                raise
            except HoudinError as error:
                self.logger.error(f"Houdin refused {entity.identifier}: {error}")
                self.state["failed"][entity.identifier] = str(error)
                continue
            self.logger.info(f"Scan {launch.scan_id} launched for {entity.identifier}, cached {launch.cached}")
            self.state["scans"][launch.scan_id] = entity.identifier

    def _enrich_completed_entities(self) -> None:
        """Write the verdict on every entity whose scan finished during this run."""
        entities_by_id: dict[str, DomainEntityInfo] = {
            entity.identifier: entity for entity in self.soar_action.target_entities
        }
        threshold: int | None = self.params.threshold
        enriched: list[DomainEntityInfo] = []
        for scan_id, document in self.documents.items():
            identifier: str = self.state["scans"][scan_id]
            self.state["done"].append(scan_id)
            entity: DomainEntityInfo | None = entities_by_id.get(identifier)
            if entity is None:
                continue
            entity.additional_properties.update(enrichment_fields(document))
            entity.is_enriched = True
            score: int | float | None = verdict_of(document)["score"]
            if threshold is not None and score is not None and score >= threshold:
                entity.is_suspicious = True
            if self.params.create_insight:
                self.entity_insights.append(
                    EntityInsight(entity=entity, message=insight_content(document), triggered_by=INTEGRATION_NAME),
                )
            enriched.append(entity)
            self.logger.info(f"{identifier}: {verdict_line(document)}")
        if enriched:
            self.soar_action.update_entities(enriched)

    def _build_final_results(self) -> None:
        """Every scan is in: the JSON result holds the full document of each one.

        The scans that finished during this run are already in hand; only the ones
        enriched by an earlier run are read again.
        """
        documents: dict[str, SingleJson] = dict(self.documents)
        earlier: list[str] = [scan_id for scan_id in self.state["done"] if scan_id not in documents]
        if earlier:
            documents.update(self.api_client.get_results(earlier))

        json_results: list[SingleJson] = []
        lines: list[str] = []
        for scan_id in self.state["done"]:
            document: SingleJson | None = documents.get(scan_id)
            if document is None:
                continue
            identifier: str = self.state["scans"][scan_id]
            json_results.append({"Entity": identifier, "EntityResult": document})
            lines.append(f"{identifier}: {verdict_line(document)} ({scan_link(scan_id)})")
        for identifier, reason in self.state["failed"].items():
            lines.append(f"{identifier}: not scanned, {reason}")

        self.json_results = json_results
        if json_results:
            self.result_value = True
            self.output_message = SUCCESS_MESSAGE.format(
                count=plural(len(json_results), "entity", "entities"),
                lines="\n".join(lines),
            )
        else:
            self.result_value = False
            self.output_message = NO_ENTITIES_MESSAGE + ("\n" + "\n".join(lines) if lines else "")


def plural(count: int, one: str, many: str) -> str:
    return f"{count} {one if count == 1 else many}"


def main() -> None:
    EnrichEntities().run()


if __name__ == "__main__":
    main()
