"""Enrich Indicator - Get threat intelligence details for an IOC from SOCRadar."""
from __future__ import annotations
import json
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from ..core.SOCRadarManager import SOCRadarManager

INTEGRATION_NAME = "SOCRadar"


def _score_to_severity(score: float | list | None) -> str:
    """Convert numeric score to severity label.
    CRITICAL: 75-100, HIGH: 50-74, MEDIUM: 25-49, LOW: 0-24
    """
    if score is None:
        return "LOW"
    if isinstance(score, list):
        score = score[0] if score else 0
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
    siemplify.script_name = "SOCRadar - Enrich Indicator"

    api_root = siemplify.extract_configuration_param(INTEGRATION_NAME, "API Root")
    api_key = siemplify.extract_configuration_param(INTEGRATION_NAME, "API Key")
    company_id = siemplify.extract_configuration_param(INTEGRATION_NAME, "Company ID")
    verify_ssl = siemplify.extract_configuration_param(INTEGRATION_NAME, "Verify SSL",
                                                       input_type=bool, default_value=True)
    ioc_api_key = siemplify.extract_configuration_param(INTEGRATION_NAME, "IOC Enrichment API Key",
                                                         default_value="")

    indicator = siemplify.extract_action_param("Indicator", is_mandatory=True)
    include_ai = siemplify.extract_action_param("Include AI Insight", is_mandatory=False,
                                                 default_value="false")
    fields_raw = siemplify.extract_action_param("Fields", is_mandatory=False, default_value="")

    if fields_raw:
        fields = [f.strip() for f in fields_raw.split(",") if f.strip()]
    else:
        fields = ["indicator_details", "indicator_history", "indicator_relations"]
        if include_ai.lower() == "true":
            fields.append("indicator_ai_insight")

    if not ioc_api_key:
        siemplify.end("IOC Enrichment API Key is not configured. "
                      "Please set it in the integration configuration.", False)
        return

    try:
        manager = SOCRadarManager(api_root, api_key, company_id, verify_ssl)
        result = manager.enrich_indicator(indicator, fields=fields, ioc_api_key=ioc_api_key)
    
        # Add severity based on score
        if isinstance(result, dict):
            details = result.get("details", {})
            raw_score = details.get("score") if isinstance(details, dict) else None
            severity = _score_to_severity(raw_score)
            result["severity"] = severity
            try:
                numeric_score = float(raw_score[0]) if isinstance(raw_score, list) and raw_score else (float(raw_score) if raw_score else 0)
            except (ValueError, TypeError):
                numeric_score = 0
            result["risk_score"] = round(numeric_score, 2)
    
        siemplify.result.add_result_json(result)
    
        # Build summary
        score_val = result.get("risk_score", "") if isinstance(result, dict) else ""
        severity_val = result.get("severity", "") if isinstance(result, dict) else ""
    
        summary = f"Enriched indicator: {indicator}"
        if score_val:
            summary += f" | Score: {score_val}"
        if severity_val:
            summary += f" | Severity: {severity_val}"
    
        # Categorization summary
        if isinstance(result, dict):
            cats = result.get("categorization", {})
            if isinstance(cats, dict):
                active = [k for k, v in cats.items() if v]
                if active:
                    summary += f" | Categories: {', '.join(active)}"
    
        credit = result.get("api_credit", {}) if isinstance(result, dict) else {}
        if isinstance(credit, dict) and credit.get("remaining_credit") is not None:
            summary += f" | Credits: {credit['remaining_credit']}"
    
        details = result.get("details") if isinstance(result, dict) else None
        has_results = bool(details.get("feed_source_list")) if isinstance(details, dict) else False
        siemplify.end(summary, has_results)
    
    except Exception as e:
        siemplify.end(f'Error executing action "Enrich Indicator". Reason: {e}', False)


if __name__ == "__main__":
    main()
