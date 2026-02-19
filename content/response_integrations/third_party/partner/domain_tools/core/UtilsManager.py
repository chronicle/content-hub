from __future__ import annotations

import urllib.parse
from typing import Any

from domaintools import utils


def chunks(lst, n):
    """ Yield successive n-sized chunks from a list """
    for i in range(0, len(lst), n):
        yield lst[i : i + n]


def convert_list_to_comma_string(values_list) -> str:
    """
    Convert list to comma-separated string

    Args:
        values_list (str): List of values

    Returns:
        str: String with comma-separated values

    """
    return (
        ", ".join(str(v) for v in values_list)
        if values_list and isinstance(values_list, list)
        else values_list
    )


def extract_domain_from_string(string: str) -> str:
    """Extracts a domain name from a URL or email address.

    Args:
        string (str): The input string which can be a URL, email, or domain.

    Returns:
        str: The extracted domain name.
    """
    string = string.lower()
    if "@" in string:
        return string.split("@")[-1]
    if string.startswith("www"):
        return string.split("www.")[-1]
    return urllib.parse.urlparse(string).netloc or string


def get_domain_risk_score_details(domain_risk: dict[str, Any]) -> dict[str, Any]:
    """Get the domain risk score details on a given domain risk

    Args:
        domain_risk (dict[str, Any]): The domain risk attribute of a domain

    Returns:
        dict[str, Any]: The detailed risk scores.
    """
    risk_scores = {
        "overall_risk_score": 0,
        "proximity_risk_score": "",
        "threat_profile_risk_score": "",
        "threat_profile_malware_risk_score": "",
        "threat_profile_phishing_risk_score": "",
        "threat_profile_spam_risk_score": "",
        "threat_profile_threats": "",
        "threat_profile_evidence": "",
    }

    risk_scores["overall_risk_score"] = domain_risk.get("risk_score")
    risk_components = domain_risk.get("components") or []
    if risk_components:
        proximity_data = utils.get_threat_component(risk_components, "proximity")
        blacklist_data = utils.get_threat_component(risk_components, "blacklist")
        if proximity_data:
            risk_scores["proximity_risk_score"] = proximity_data.get("risk_score") or ""
        elif blacklist_data:
            risk_scores["proximity_risk_score"] = blacklist_data.get("risk_score") or ""

        threat_profile_data = utils.get_threat_component(risk_components, "threat_profile")
        if threat_profile_data:
            risk_scores["threat_profile_risk_score"] = threat_profile_data.get("risk_score") or ""
            risk_scores["threat_profile_threats"] = ", ".join(threat_profile_data.get("threats", []))
            risk_scores["threat_profile_evidence"] = ", ".join(threat_profile_data.get("evidence", []))
        threat_profile_malware_data = utils.get_threat_component(risk_components, "threat_profile_malware")
        if threat_profile_malware_data:
            risk_scores["threat_profile_malware_risk_score"] = threat_profile_malware_data.get("risk_score") or ""
        threat_profile_phshing_data = utils.get_threat_component(risk_components, "threat_profile_phishing")
        if threat_profile_phshing_data:
            risk_scores["threat_profile_phishing_risk_score"] = threat_profile_phshing_data.get("risk_score") or ""
        threat_profile_spam_data = utils.get_threat_component(risk_components, "threat_profile_spam")
        if threat_profile_spam_data:
            risk_scores["threat_profile_spam_risk_score"] = threat_profile_spam_data.get("risk_score", 0)

    return risk_scores
