from __future__ import annotations
import json

from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyDataModel import InsightSeverity, InsightType
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED

from ..core.config import Config
from ..core.UtilsManager import GIBConnector


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = "Get Violation Details"

    status = EXECUTION_STATE_COMPLETED
    result_value = False
    output_messages = []

    poller = GIBConnector(siemplify).init_action_poller()

    siemplify.LOGGER.info('──── GATHER ENTITIES')

    # Build URL → UID lookup once from event data
    url_to_uid = {}
    for event in siemplify.current_alert.security_events:
        props = getattr(event, 'additional_properties', {}) or {}
        url = props.get("violation_url", "").lower()
        uid_val = props.get("violation_uid", "")
        if url and uid_val and url not in url_to_uid:
            url_to_uid[url] = uid_val
    siemplify.LOGGER.info("Built URL→UID map with {} entries".format(len(url_to_uid)))

    results = []

    for entity in siemplify.target_entities:
        if entity.entity_type != "DestinationURL":
            continue

        uid = url_to_uid.get(entity.identifier.lower())

        if not uid:
            siemplify.LOGGER.error("No violation UID found for entity: {}".format(entity.identifier))
            output_messages.append("No UID found for: {}".format(entity.identifier))
            status = EXECUTION_STATE_FAILED
            continue

        siemplify.LOGGER.info("Fetching violation: {}".format(uid))

        try:
            parser = poller.search_feed_by_id(feed_id=uid)
            raw = parser.raw_dict

            violation = raw.get("violation", {})
            scores = {s["type"]: s["score"] for s in violation.get("scores", [])}

            result = {
                "id": raw.get("id"),
                "brand": raw.get("brand"),
                "company": raw.get("company"),
                "link": raw.get("link"),
                "images": raw.get("images"),
                "uri": violation.get("uri"),
                "status": violation.get("status"),
                "approveState": violation.get("approveState"),
                "violationType": violation.get("violationType"),
                "violationSubtype": violation.get("violationSubtype"),
                "workerCodes": violation.get("workerCodes"),
                "title": violation.get("title"),
                "description": violation.get("description"),
                "tags": violation.get("tags"),
                "score_domain": scores.get("domain"),
                "score_risk": scores.get("risk"),
                "firstDetected": violation.get("firstDetected"),
                "firstActive": violation.get("firstActive"),
                "firstSolved": violation.get("firstSolved"),
                "dates": violation.get("dates"),
                "stages": violation.get("stages"),
            }

            results.append(result)
            output_messages.append("Fetched violation details for: {}".format(entity.identifier))
            result_value = True

            insight_lines = [
                "<b>Violation ID:</b> {}".format(uid),
                "<b>Status:</b> {}".format(result.get("status", "N/A")),
                "<b>Approve State:</b> {}".format(result.get("approveState", "N/A")),
                "<b>Type:</b> {}".format(result.get("violationType", "N/A")),
                "<b>Subtype:</b> {}".format(result.get("violationSubtype", "N/A")),
                "<b>Title:</b> {}".format(result.get("title", "N/A")),
                "<b>Brand:</b> {}".format(result.get("brand", "N/A")),
                "<b>Score (domain):</b> {}".format(result.get("score_domain", "N/A")),
                "<b>Score (risk):</b> {}".format(result.get("score_risk", "N/A")),
                "<b>First Detected:</b> {}".format(result.get("firstDetected", "N/A")),
                "<b>First Active:</b> {}".format(result.get("firstActive", "N/A")),
                "<b>Link:</b> {}".format(result.get("link", "N/A")),
            ]
            siemplify.create_case_insight(
                triggered_by="Get Violation Details",
                title="Group-IB Violation Details",
                content="<br>".join(insight_lines),
                entity_identifier=entity.identifier,
                severity=InsightSeverity.INFO,
                insight_type=InsightType.Entity
            )

        except Exception as e:
            siemplify.LOGGER.error("Failed for entity {}: {}".format(entity.identifier, e))
            siemplify.LOGGER.exception(e)
            output_messages.append("Failed to fetch violation details for: {}".format(entity.identifier))
            status = EXECUTION_STATE_FAILED

    if not results and status != EXECUTION_STATE_FAILED:
        output_messages.append("No DestinationURL entities with a violation ID were found.")
        status = EXECUTION_STATE_FAILED

    if results:
        siemplify.result.add_result_json(json.dumps(results if len(results) > 1 else results[0]))

    siemplify.end("\n".join(output_messages), result_value, status)


if __name__ == "__main__":
    main()
