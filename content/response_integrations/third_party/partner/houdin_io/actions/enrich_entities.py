from __future__ import annotations

import json

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED, EXECUTION_STATE_INPROGRESS
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

from ..core.houdin import HoudinAccountError, HoudinError, HoudinManager
from ..core.houdin_constants import (
    DEFAULT_SUSPICIOUS_THRESHOLD,
    ENRICH_ENTITIES_SCRIPT_NAME,
    INTEGRATION_NAME,
)
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

SUPPORTED_TYPES_NOTE = (
    "Supported entities: public IPv4 and IPv6 addresses, URLs, domains and hostnames, MD5, SHA1 and SHA256 hashes."
)


@output_handler
def main() -> None:
    siemplify = SiemplifyAction()
    siemplify.script_name = ENRICH_ENTITIES_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    api_root = siemplify.extract_configuration_param(INTEGRATION_NAME, param_name="API Root")
    api_key = siemplify.extract_configuration_param(INTEGRATION_NAME, param_name="API Key")
    verify_ssl = siemplify.extract_configuration_param(
        INTEGRATION_NAME, param_name="Verify SSL", default_value=True, input_type=bool
    )
    scanners = parse_scanners(siemplify.extract_action_param("Scanners", print_value=True))
    force_rescan = siemplify.extract_action_param("Force Rescan", input_type=bool, default_value=False)
    create_insight = siemplify.extract_action_param("Create Insight", input_type=bool, default_value=True)
    threshold_raw = siemplify.extract_action_param("Suspicious Threshold", print_value=True)
    state = load_state(siemplify.extract_action_param("additional_data"))

    try:
        threshold = parse_threshold(threshold_raw, DEFAULT_SUSPICIOUS_THRESHOLD)
        houdin = HoudinManager(api_key, api_root, verify_ssl)
        entities_by_id = {entity.identifier: entity for entity in siemplify.target_entities}

        # The state carried between runs: scanID -> entity identifier for every
        # launched scan, the scanIDs already enriched, and the entities that
        # could not be scanned with the reason.
        if state is None:
            state = {"scans": {}, "done": [], "failed": {}}
            for entity in siemplify.target_entities:
                if not is_scannable_entity(entity):
                    siemplify.LOGGER.info(f"Skipping {entity.identifier} ({entity.entity_type}): not scannable")
                    continue
                try:
                    launch = houdin.launch_scan(entity.identifier, scanners, force_rescan)
                except HoudinAccountError:
                    raise
                except HoudinError as error:
                    siemplify.LOGGER.error(f"Houdin refused {entity.identifier}: {error}")
                    state["failed"][entity.identifier] = str(error)
                    continue
                siemplify.LOGGER.info(f"Scan {launch.scan_id} launched for {entity.identifier}, cached {launch.cached}")
                state["scans"][launch.scan_id] = entity.identifier

        pending = [scan_id for scan_id in state["scans"] if scan_id not in state["done"]]
        documents = houdin.wait_for_results(pending) if pending else {}

        enriched = []
        for scan_id, document in documents.items():
            identifier = state["scans"][scan_id]
            entity = entities_by_id.get(identifier)
            state["done"].append(scan_id)
            if entity is None:
                continue
            entity.additional_properties.update(enrichment_fields(document))
            entity.is_enriched = True
            score = verdict_of(document)["score"]
            if threshold is not None and score is not None and score >= threshold:
                entity.is_suspicious = True
            if create_insight:
                siemplify.add_entity_insight(entity, insight_content(document), triggered_by=INTEGRATION_NAME)
            enriched.append(entity)
            siemplify.LOGGER.info(f"{identifier}: {verdict_line(document)}")
        if enriched:
            siemplify.update_entities(enriched)

        still_running = [scan_id for scan_id in state["scans"] if scan_id not in state["done"]]
        if still_running:
            waiting = ", ".join(state["scans"][scan_id] for scan_id in still_running)
            siemplify.LOGGER.info(f"Waiting on {len(still_running)} scan(s): {waiting}")
            siemplify.end(
                f"Houdin is still scanning {plural(len(still_running), 'entity', 'entities')}: {waiting}",
                json.dumps(state),
                EXECUTION_STATE_INPROGRESS,
            )
            return

        # Every scan is in: build the JSON result from the full documents in one call.
        json_results = []
        lines = []
        if state["done"]:
            for scan_id, document in houdin.get_results(state["done"]).items():
                identifier = state["scans"][scan_id]
                json_results.append({"Entity": identifier, "EntityResult": document})
                lines.append(f"{identifier}: {verdict_line(document)} ({scan_link(scan_id)})")
        for identifier, reason in state["failed"].items():
            lines.append(f"{identifier}: not scanned, {reason}")

        siemplify.result.add_result_json(json_results)
        if json_results:
            output_message = f"Enriched {plural(len(json_results), 'entity', 'entities')} with Houdin:\n"
            output_message += "\n".join(lines)
        else:
            output_message = "No entity was scanned. " + SUPPORTED_TYPES_NOTE
            if lines:
                output_message += "\n" + "\n".join(lines)
        siemplify.LOGGER.info(output_message)
        siemplify.end(output_message, len(json_results), EXECUTION_STATE_COMPLETED)

    except HoudinError as error:
        siemplify.LOGGER.error(f"Houdin refused the request: {error}")
        siemplify.end(f"Houdin could not enrich the entities: {error}", "false", EXECUTION_STATE_FAILED)
    except Exception as error:
        siemplify.LOGGER.error(f"Enrich Entities failed: {error}")
        siemplify.LOGGER.exception(error)
        siemplify.end(f"Error executing action Enrich Entities. Reason: {error}", "false", EXECUTION_STATE_FAILED)


def plural(count: int, one: str, many: str) -> str:
    return f"{count} {one if count == 1 else many}"


if __name__ == "__main__":
    main()
