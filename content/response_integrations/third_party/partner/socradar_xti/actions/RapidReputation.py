"""Rapid Reputation - Quick reputation check for an entity from SOCRadar."""
from __future__ import annotations
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from ..core.SOCRadarManager import SOCRadarManager

INTEGRATION_NAME = "SOCRadar"
VALID_ENTITY_TYPES = ["ip", "hostname", "url", "hash"]


def _score_to_severity(score: float | None) -> str:
    """Convert numeric score to severity label.
    CRITICAL: 75-100, HIGH: 50-74, MEDIUM: 25-49, LOW: 0-24
    """
    if score is None:
        return "LOW"
    try:
        score = float(score)
    except (ValueError, TypeError):
        return "LOW"
    if score >= 75:
        return "CRITICAL"
    if score >= 50:
        return "HIGH"
    if score >= 25:
        return "MEDIUM"
    return "LOW"


@output_handler
def main() -> None:
    siemplify = SiemplifyAction()
    siemplify.script_name = "SOCRadar - Rapid Reputation"

    api_root = siemplify.extract_configuration_param(INTEGRATION_NAME, "API Root")
    api_key = siemplify.extract_configuration_param(INTEGRATION_NAME, "API Key")
    company_id = siemplify.extract_configuration_param(INTEGRATION_NAME, "Company ID")
    verify_ssl = siemplify.extract_configuration_param(INTEGRATION_NAME, "Verify SSL",
                                                       input_type=bool, default_value=True)
    rapid_api_key = siemplify.extract_configuration_param(INTEGRATION_NAME, "Rapid Reputation API Key",
                                                           default_value="")

    entity_value = siemplify.extract_action_param("Entity Value", is_mandatory=True)
    entity_type = siemplify.extract_action_param("Entity Type", is_mandatory=True).lower()

    if entity_type not in VALID_ENTITY_TYPES:
        siemplify.end(f"Invalid entity type: {entity_type}. Must be one of: {VALID_ENTITY_TYPES}", False)
        return

    if not rapid_api_key:
        siemplify.end("Rapid Reputation API Key is not configured. "
                      "Please set it in the integration configuration.", False)
        return

    try:
        manager = SOCRadarManager(api_root, api_key, company_id, verify_ssl)
        result = manager.rapid_reputation(entity_value, entity_type, rapid_api_key=rapid_api_key)
    
        # Add severity based on score
        data = result.get("data") if isinstance(result, dict) else {}
        if not isinstance(data, dict):
            data = {}
        score = data.get("score")
        severity = _score_to_severity(score)
        if isinstance(result, dict):
            result["severity"] = severity
            try:
                result["risk_score"] = round(float(score), 2) if score is not None else 0
            except (ValueError, TypeError):
                result["risk_score"] = 0
    
        siemplify.result.add_result_json(result)
    
        whitelisted = data.get("is_whitelisted", False)
        sources = data.get("finding_sources", [])
    
        summary = f"Reputation for {entity_type}:{entity_value}"
        if score is not None:
            summary += f" | Score: {round(float(score), 2)}"
        summary += f" | Severity: {severity}"
        if whitelisted:
            summary += " | WHITELISTED"
        summary += f" | {len(sources)} source(s)"
    
        siemplify.end(summary, True)
    
    except Exception as e:
        siemplify.end(f"Action failed: {e}", False)


if __name__ == "__main__":
    main()
