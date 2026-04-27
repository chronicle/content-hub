from __future__ import annotations

from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED

from ..core.config import Config
from ..core.UtilsManager import GIBConnector


@output_handler
def main() -> None:
    """Reject DRP violation URLs that match target entities of the action.

    Walks the alert's security events to build a URL→violation-UID map, then
    iterates over the action's target entities. For every ``DestinationURL``
    entity with a known UID it submits a reject request to the DRP API and
    records the outcome (rejected / failed / unmapped) per entity. Failures of
    individual entities do not abort the action — they are aggregated into the
    final output message and the action exits with ``EXECUTION_STATE_FAILED``
    only if at least one entity could not be rejected.
    """

    siemplify = SiemplifyAction()
    siemplify.script_name = Config.GC_REJECT_SCRIPT_NAME

    poller = GIBConnector(siemplify).init_action_poller()

    siemplify.LOGGER.info('──── GATHER ENTITIES')

    received_entities = [(entity.identifier, entity.entity_type) for entity in siemplify.target_entities]

    siemplify.LOGGER.info('──── PARSE DATA')

    url_to_uid = {}
    for event in siemplify.current_alert.security_events:
        props = getattr(event, 'additional_properties', {}) or {}
        url = props.get("violation_url", "").lower()
        uid_val = props.get("violation_uid", "")
        if url and uid_val and url not in url_to_uid:
            url_to_uid[url] = uid_val

    rejected_ids = []
    failed_ids = []
    unmapped_ids = []

    for _entity, _entity_type in received_entities:
        siemplify.LOGGER.info("entity: {}, type: {}".format(_entity, _entity_type))

        if not _entity or _entity_type != "DestinationURL":
            continue

        uid = url_to_uid.get(_entity.lower())
        if not uid:
            siemplify.LOGGER.error("No violation UID found for entity: {}".format(_entity))
            unmapped_ids.append(_entity)
            continue

        data = {"violationId": uid, "approve": False}
        params = {"q": None}

        siemplify.LOGGER.info("data: {}".format(data))

        try:
            res = poller.send_request(
                endpoint="violation/change-approve",
                params=params,
                method="POST",
                json=data,
            )
            siemplify.LOGGER.info(res)
            rejected_ids.append(_entity)
        except Exception as e:
            siemplify.LOGGER.error("Reject failed for entity {} (uid={}): {}".format(_entity, uid, e))
            siemplify.LOGGER.exception(e)
            failed_ids.append(_entity)

    summary_lines = []
    if rejected_ids:
        summary_lines.append("Rejected: {}".format(", ".join(rejected_ids)))
    if failed_ids:
        summary_lines.append("Failed: {}".format(", ".join(failed_ids)))
    if unmapped_ids:
        summary_lines.append("No matching violation UID: {}".format(", ".join(unmapped_ids)))
    if not summary_lines:
        summary_lines.append("No DestinationURL entities to reject.")

    output_message = "\n".join(summary_lines)
    result_value = bool(rejected_ids)
    status = EXECUTION_STATE_FAILED if failed_ids else EXECUTION_STATE_COMPLETED

    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
