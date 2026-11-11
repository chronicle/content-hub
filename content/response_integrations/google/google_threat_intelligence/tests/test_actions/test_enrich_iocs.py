from __future__ import annotations

from TIPCommon.types import SingleJson

from google_threat_intelligence.actions import enrich_iocs
from google_threat_intelligence.tests.common import CONFIG_PATH
from google_threat_intelligence.tests.core.product import (
    GoogleThreatIntelligenceProduct,
)
from google_threat_intelligence.tests.core.session import (
    GoogleThreatIntelligenceSession,
)
from google_threat_intelligence.tests.responses.api import common_responses
from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata

SUCCESS_OUTPUT_MESSAGE: str = (
    "Successfully enriched the following IOCs using Google Threat Intelligence: \n"
)
INVALID_IOC_MSG = "No information about IOCs was found."

INTEGRATION_PARAMETERS: SingleJson = {
    "Scope": "All entities",
    "Test case": "Case1",
    "Integration Instance": "Instance1",
    "IOC Type": "",
    "IOCs": "",
}

NON_MALICIOUS_IP: str = "8.8.8.8"
INTEGRATION_PARAMETERS_IP_NON_MALICIOUS: SingleJson = INTEGRATION_PARAMETERS.copy()
INTEGRATION_PARAMETERS_IP_NON_MALICIOUS["IOC Type"] = "IP Address"
INTEGRATION_PARAMETERS_IP_NON_MALICIOUS["IOCs"] = NON_MALICIOUS_IP


@set_metadata(
    parameters=INTEGRATION_PARAMETERS_IP_NON_MALICIOUS,
    integration_config_file_path=CONFIG_PATH,
)
def test_enrich_ioc_ip_address_non_malicious(
    google_threat_intelligence_product: GoogleThreatIntelligenceSession,
    script_session: GoogleThreatIntelligenceProduct,
    action_output: MockActionOutput,
) -> None:
    google_threat_intelligence_product.add_ioc(
        NON_MALICIOUS_IP,
        common_responses.NON_MALICIOUS_IP_RESPONSE,
    )
    enrich_iocs.main()

    assert len(script_session.request_history) == 4
    assert (
        action_output.results.output_message
        == SUCCESS_OUTPUT_MESSAGE + f"{NON_MALICIOUS_IP}"
    )
    assert (
        action_output.results.json_output.json_result["iocs"][0]
        .get("details")
        .get("attributes")
        .get("gti_assessment")
        .get("verdict")
        .get("value")
        == "VERDICT_BENIGN"
    )
    assert action_output.results.result_value is True


MALICIOUS_IP: str = "103.138.13.31"
INTEGRATION_PARAMETERS_IP_MALICIOUS: SingleJson = INTEGRATION_PARAMETERS.copy()
INTEGRATION_PARAMETERS_IP_MALICIOUS["IOC Type"] = "IP Address"
INTEGRATION_PARAMETERS_IP_MALICIOUS["IOCs"] = MALICIOUS_IP


@set_metadata(
    parameters=INTEGRATION_PARAMETERS_IP_MALICIOUS,
    integration_config_file_path=CONFIG_PATH,
)
def test_enrich_ioc_ip_address_malicious(
    google_threat_intelligence_product: GoogleThreatIntelligenceSession,
    script_session: GoogleThreatIntelligenceProduct,
    action_output: MockActionOutput,
) -> None:
    google_threat_intelligence_product.add_ioc(
        MALICIOUS_IP,
        common_responses.MALICIOUS_IP_RESPONSE,
    )
    enrich_iocs.main()

    assert len(script_session.request_history) == 4
    assert (
        action_output.results.output_message
        == SUCCESS_OUTPUT_MESSAGE + f"{MALICIOUS_IP}"
    )
    assert (
        action_output.results.json_output.json_result["iocs"][0]
        .get("details")
        .get("attributes")
        .get("gti_assessment")
        .get("verdict")
        .get("value")
        == "VERDICT_MALICIOUS"
    )
    assert action_output.results.result_value is True


NON_MALICIOUS_URL: str = "https://www.google.com"
INTEGRATION_PARAMETERS_URL_NON_MALICIOUS: SingleJson = INTEGRATION_PARAMETERS.copy()
INTEGRATION_PARAMETERS_URL_NON_MALICIOUS["IOC Type"] = "URL"
INTEGRATION_PARAMETERS_URL_NON_MALICIOUS["IOCs"] = NON_MALICIOUS_URL


@set_metadata(
    parameters=INTEGRATION_PARAMETERS_URL_NON_MALICIOUS,
    integration_config_file_path=CONFIG_PATH,
)
def test_enrich_ioc_url_non_malicious(
    google_threat_intelligence_product: GoogleThreatIntelligenceSession,
    script_session: GoogleThreatIntelligenceProduct,
    action_output: MockActionOutput,
) -> None:
    google_threat_intelligence_product.add_ioc(
        NON_MALICIOUS_URL,
        common_responses.NON_MALICIOUS_URL_RESPONSE,
    )
    enrich_iocs.main()

    assert len(script_session.request_history) == 4
    assert (
        action_output.results.output_message
        == SUCCESS_OUTPUT_MESSAGE + f"{NON_MALICIOUS_URL}"
    )
    assert (
        action_output.results.json_output.json_result["iocs"][0]
        .get("details")
        .get("attributes")
        .get("gti_assessment")
        .get("verdict")
        .get("value")
        == "VERDICT_UNDETECTED"
    )
    assert action_output.results.result_value is True


MALICIOUS_URL: str = "http://54.37.72.170/n3"
INTEGRATION_PARAMETERS_URL_MALICIOUS: SingleJson = INTEGRATION_PARAMETERS.copy()
INTEGRATION_PARAMETERS_URL_MALICIOUS["IOC Type"] = "URL"
INTEGRATION_PARAMETERS_URL_MALICIOUS["IOCs"] = MALICIOUS_URL


@set_metadata(
    parameters=INTEGRATION_PARAMETERS_URL_MALICIOUS,
    integration_config_file_path=CONFIG_PATH,
)
def test_enrich_ioc_url_malicious(
    google_threat_intelligence_product: GoogleThreatIntelligenceSession,
    script_session: GoogleThreatIntelligenceProduct,
    action_output: MockActionOutput,
) -> None:
    google_threat_intelligence_product.add_ioc(
        MALICIOUS_URL,
        common_responses.MALICIOUS_URL_RESPONSE,
    )
    enrich_iocs.main()

    assert len(script_session.request_history) == 4
    assert (
        action_output.results.output_message
        == SUCCESS_OUTPUT_MESSAGE + f"{MALICIOUS_URL}"
    )
    assert (
        action_output.results.json_output.json_result["iocs"][0]
        .get("details")
        .get("attributes")
        .get("gti_assessment")
        .get("verdict")
        .get("value")
        == "VERDICT_MALICIOUS"
    )
    assert action_output.results.result_value is True


NON_MALICIOUS_FILE_HASH: str = (
    "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
)
INTEGRATION_PARAMETERS_FILE_HASH_NON_MALICIOUS: SingleJson = (
    INTEGRATION_PARAMETERS.copy()
)
INTEGRATION_PARAMETERS_FILE_HASH_NON_MALICIOUS["IOC Type"] = "Filehash"
INTEGRATION_PARAMETERS_FILE_HASH_NON_MALICIOUS["IOCs"] = NON_MALICIOUS_FILE_HASH


@set_metadata(
    parameters=INTEGRATION_PARAMETERS_FILE_HASH_NON_MALICIOUS,
    integration_config_file_path=CONFIG_PATH,
)
def test_enrich_ioc_file_hash_non_malicious(
    google_threat_intelligence_product: GoogleThreatIntelligenceSession,
    script_session: GoogleThreatIntelligenceProduct,
    action_output: MockActionOutput,
) -> None:
    google_threat_intelligence_product.add_ioc(
        NON_MALICIOUS_FILE_HASH,
        common_responses.NON_MALICIOUS_FILE_HASH_RESPONSE,
    )
    enrich_iocs.main()

    assert len(script_session.request_history) == 4
    assert (
        action_output.results.output_message
        == SUCCESS_OUTPUT_MESSAGE + f"{NON_MALICIOUS_FILE_HASH}"
    )
    assert (
        action_output.results.json_output.json_result["iocs"][0]
        .get("details")
        .get("attributes")
        .get("gti_assessment")
        .get("verdict")
        .get("value")
        == "VERDICT_BENIGN"
    )
    assert action_output.results.result_value is True


MALICIOUS_FILE_HASH: str = (
    "178ba564b39bd07577e974a9b677dfd86ffa1f1d0299dfd958eb883c5ef6c3e1"
)
INTEGRATION_PARAMETERS_FILE_HASH_MALICIOUS: SingleJson = INTEGRATION_PARAMETERS.copy()
INTEGRATION_PARAMETERS_FILE_HASH_MALICIOUS["IOC Type"] = "Filehash"
INTEGRATION_PARAMETERS_FILE_HASH_MALICIOUS["IOCs"] = MALICIOUS_FILE_HASH


@set_metadata(
    parameters=INTEGRATION_PARAMETERS_FILE_HASH_MALICIOUS,
    integration_config_file_path=CONFIG_PATH,
)
def test_enrich_ioc_file_hash_malicious(
    google_threat_intelligence_product: GoogleThreatIntelligenceSession,
    script_session: GoogleThreatIntelligenceProduct,
    action_output: MockActionOutput,
) -> None:
    google_threat_intelligence_product.add_ioc(
        MALICIOUS_FILE_HASH,
        common_responses.MALICIOUS_FILE_HASH_RESPONSE,
    )
    enrich_iocs.main()

    assert len(script_session.request_history) == 4
    assert (
        action_output.results.output_message
        == SUCCESS_OUTPUT_MESSAGE + f"{MALICIOUS_FILE_HASH}"
    )
    assert (
        action_output.results.json_output.json_result["iocs"][0]
        .get("details")
        .get("attributes")
        .get("gti_assessment")
        .get("verdict")
        .get("value")
        == "VERDICT_MALICIOUS"
    )
    assert action_output.results.result_value is True


INVALID_FILE_HASH: str = "'178ba564b39bd07577e974a0299dfd958eb883c5ef6c3e1'"
INTEGRATION_PARAMETERS_FILE_HASH_INVALID: SingleJson = INTEGRATION_PARAMETERS.copy()
INTEGRATION_PARAMETERS_FILE_HASH_INVALID["IOC Type"] = "Filehash"
INTEGRATION_PARAMETERS_FILE_HASH_INVALID["IOCs"] = INVALID_FILE_HASH


@set_metadata(
    parameters=INTEGRATION_PARAMETERS_FILE_HASH_INVALID,
    integration_config_file_path=CONFIG_PATH,
)
def test_enrich_ioc_file_hash_invalid(
    google_threat_intelligence_product: GoogleThreatIntelligenceSession,
    script_session: GoogleThreatIntelligenceProduct,
    action_output: MockActionOutput,
) -> None:
    google_threat_intelligence_product.add_ioc(INVALID_FILE_HASH, None)
    enrich_iocs.main()

    assert len(script_session.request_history) == 2
    assert action_output.results.output_message == INVALID_IOC_MSG
    assert action_output.results.result_value is False


MALICIOUS_DOMAIN: str = "aramelochpetinnew2.ddns.net"
INTEGRATION_PARAMETERS_DOMAIN_MALICIOUS: SingleJson = INTEGRATION_PARAMETERS.copy()
INTEGRATION_PARAMETERS_DOMAIN_MALICIOUS["IOC Type"] = "Domain"
INTEGRATION_PARAMETERS_DOMAIN_MALICIOUS["IOCs"] = MALICIOUS_DOMAIN


@set_metadata(
    parameters=INTEGRATION_PARAMETERS_DOMAIN_MALICIOUS,
    integration_config_file_path=CONFIG_PATH,
)
def test_enrich_ioc_domain_malicious(
    google_threat_intelligence_product: GoogleThreatIntelligenceSession,
    script_session: GoogleThreatIntelligenceProduct,
    action_output: MockActionOutput,
) -> None:
    google_threat_intelligence_product.add_ioc(
        MALICIOUS_DOMAIN,
        common_responses.MALICIOUS_DOMAIN_RESPONSE,
    )
    enrich_iocs.main()

    assert len(script_session.request_history) == 4
    assert (
        action_output.results.output_message
        == SUCCESS_OUTPUT_MESSAGE + f"{MALICIOUS_DOMAIN}"
    )
    assert (
        action_output.results.json_output.json_result["iocs"][0]
        .get("details")
        .get("attributes")
        .get("gti_assessment")
        .get("verdict")
        .get("value")
        == "VERDICT_MALICIOUS"
    )
    assert action_output.results.result_value is True


NON_MALICIOUS_DOMAIN: str = "google.com"
INTEGRATION_PARAMETERS_DOMAIN_NON_MALICIOUS: SingleJson = INTEGRATION_PARAMETERS.copy()
INTEGRATION_PARAMETERS_DOMAIN_NON_MALICIOUS["IOC Type"] = "Domain"
INTEGRATION_PARAMETERS_DOMAIN_NON_MALICIOUS["IOCs"] = NON_MALICIOUS_DOMAIN


@set_metadata(
    parameters=INTEGRATION_PARAMETERS_DOMAIN_NON_MALICIOUS,
    integration_config_file_path=CONFIG_PATH,
)
def test_enrich_ioc_domain_non_malicious(
    google_threat_intelligence_product: GoogleThreatIntelligenceSession,
    script_session: GoogleThreatIntelligenceProduct,
    action_output: MockActionOutput,
) -> None:
    google_threat_intelligence_product.add_ioc(
        NON_MALICIOUS_DOMAIN,
        common_responses.NON_MALICIOUS_DOMAIN_RESPONSE,
    )
    enrich_iocs.main()

    assert len(script_session.request_history) == 4
    assert (
        action_output.results.output_message
        == SUCCESS_OUTPUT_MESSAGE + f"{NON_MALICIOUS_DOMAIN}"
    )
    assert (
        action_output.results.json_output.json_result["iocs"][0]
        .get("details")
        .get("attributes")
        .get("gti_assessment")
        .get("verdict")
        .get("value")
        == "VERDICT_BENIGN"
    )
    assert action_output.results.result_value is True


@set_metadata(
    parameters={**INTEGRATION_PARAMETERS_IP_NON_MALICIOUS, "Widget Theme": "Light"},
    integration_config_file_path=CONFIG_PATH,
)
def test_enrich_ioc_light_theme(
    google_threat_intelligence_product: GoogleThreatIntelligenceSession,
    script_session: GoogleThreatIntelligenceProduct,
) -> None:
    google_threat_intelligence_product.add_ioc(
        NON_MALICIOUS_IP,
        common_responses.NON_MALICIOUS_IP_RESPONSE,
    )
    enrich_iocs.main()

    assert len(script_session.request_history) == 4
    # Request index 2 should be the gtiwidget request
    assert script_session.request_history[2].request.url.path == "/api/v3/gtiwidget"
    assert script_session.request_history[2].request.params.get("theme")[0] == "light"
    assert script_session.request_history[2].request.params.get("fg1")[0] == "4f5064"
    assert script_session.request_history[2].request.params.get("bg1")[0] == "ffffff"
    assert script_session.request_history[2].request.params.get("bg2")[0] == "f4f5fa"
    assert script_session.request_history[2].request.params.get("bd1")[0] == "d2d7e9"
