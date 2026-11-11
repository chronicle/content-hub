from __future__ import annotations

import base64
import zlib

from TIPCommon.base.action import EntityTypesEnum, ExecutionState
from TIPCommon.base.data_models import ActionJsonOutput, ActionOutput
from google_threat_intelligence.tests.core.product import (
    GoogleThreatIntelligenceProduct,
)
from google_threat_intelligence.tests.core.session import (
    GoogleThreatIntelligenceSession,
)
from google_threat_intelligence.tests.responses.api import common_responses
from integration_testing.common import create_entity, set_is_first_run_to_true, set_is_first_run_to_false
from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata
from google_threat_intelligence.actions import enrich_entities

EMPTY_ESCAPED_HTML_RESPONSE_WITH_FONTS = (
    "&lt;head&gt;&lt;link href=&quot;https://fonts.googleapis.com/css?family="
    "Open+Sans:300,400,500,600,700,800|Source+Sans+Pro:300,400,600,700"
    "&amp;amp;display=swap&quot; rel=&quot;stylesheet&quot;/&gt;&lt;/head&gt;"
    "&lt;body&gt;&lt;/body&gt;"
)


def get_compressed_html(raw_html_escaped: str) -> str:

    compressed = zlib.compress(raw_html_escaped.encode("utf-8"))
    b64_compressed = base64.b64encode(compressed).decode("utf-8")
    return f"COMPRESSED_ZLIB:{b64_compressed}"


INTEGRATION_CONFIG = {
    "API Root": "https://www.virustotal.com",
    "API Key": "TEST",
    "ASM Project Name": "TestProject",
    "Verify SSL": True,
}

INTEGRATION_CONFIG_NO_ASM = {
    "API Root": "https://www.virustotal.com",
    "API Key": "TEST",
    "ASM Project Name": "",
    "Verify SSL": True,
}

INPUT_PARAMETERS = {
    "Resubmit Entity": False,
    "Resubmit After (Days)": 30,
    "Sandbox": "VirusTotal Jujubox",
    "Lowest MITRE Technique Severity": "Medium",
    "Retrieve Comments": True,
    "Max Comments To Return": 10,
}

DOMAIN_IDENTIFIER1 = "https://domaiN.com"
DOMAIN_IDENTIFIER2 = "https://testSafebrowsing.appspot.com/s/malware.html"

SUCCESS_URL_ENTITIES_MESSAGE = (
    "Successfully enriched the following entities using  "
    f"Google Threat Intelligence: \n {DOMAIN_IDENTIFIER1}, "
    f"{DOMAIN_IDENTIFIER2} \n"
)

ENTITY_URL_RESULT1 = common_responses.NON_MALICIOUS_URL_RESPONSE.get("data")
ENTITY_URL_RESULT1.update(
    {
        "widget_link": common_responses.WIDGET_URL_RESPONSE["data"]["url"] + "/summary",
        "widget_html": get_compressed_html(EMPTY_ESCAPED_HTML_RESPONSE_WITH_FONTS),
        "is_risky": False,
        "execution_status": "success",
        "comments": common_responses.URL_ADDRESS_COMMENTS_RESPONSE["data"],
    }
)

ENTITY_URL_RESULT2 = common_responses.MALICIOUS_URL_RESPONSE.get("data")
ENTITY_URL_RESULT2.update(
    {
        "widget_link": common_responses.WIDGET_URL_RESPONSE["data"]["url"] + "/summary",
        "widget_html": get_compressed_html(EMPTY_ESCAPED_HTML_RESPONSE_WITH_FONTS),
        "is_risky": True,
        "execution_status": "success",
        "comments": common_responses.URL_ADDRESS_COMMENTS_RESPONSE["data"],
    }
)

RESULT_URL_ENTITIES_RESPONSE = [
    {
        "Entity": DOMAIN_IDENTIFIER1,
        "EntityResult": ENTITY_URL_RESULT1,
    },
    {
        "Entity": DOMAIN_IDENTIFIER2,
        "EntityResult": ENTITY_URL_RESULT2,
    },
]


@set_metadata(
    integration_config=INTEGRATION_CONFIG_NO_ASM,
    parameters=INPUT_PARAMETERS,
    entities=[
        create_entity(DOMAIN_IDENTIFIER1, EntityTypesEnum.URL),
        create_entity(DOMAIN_IDENTIFIER2, EntityTypesEnum.URL),
    ],
)
def test_enrich_entities_url(
    script_session: GoogleThreatIntelligenceSession,
    action_output: MockActionOutput,
    google_threat_intelligence_product: GoogleThreatIntelligenceProduct,
) -> None:
    set_is_first_run_to_true()

    google_threat_intelligence_product.add_ioc(
        ioc_identifier=DOMAIN_IDENTIFIER1,
        response_type_json=common_responses.NON_MALICIOUS_URL_RESPONSE,
    )
    google_threat_intelligence_product.add_ioc(
        ioc_identifier=DOMAIN_IDENTIFIER2,
        response_type_json=common_responses.MALICIOUS_URL_RESPONSE,
    )
    url_hash1 = common_responses.NON_MALICIOUS_URL_RESPONSE["data"]["id"]
    google_threat_intelligence_product.add_comments(
        ioc_identifier=url_hash1,
        response=common_responses.URL_ADDRESS_COMMENTS_RESPONSE,
    )
    url_hash2 = common_responses.MALICIOUS_URL_RESPONSE["data"]["id"]
    google_threat_intelligence_product.add_comments(
        ioc_identifier=url_hash2,
        response=common_responses.URL_ADDRESS_COMMENTS_RESPONSE,
    )
    enrich_entities.main()

    assert len(script_session.request_history) == 9
    assert script_session.request_history[0].request.url.path == "/api/v3/metadata"
    assert script_session.request_history[1].request.url.path.startswith("/api/v3/urls")
    assert script_session.request_history[2].request.url.path.startswith("/api/v3/urls")
    assert (
        script_session.request_history[3].request.url.path
        == f"/api/v3/urls/{ENTITY_URL_RESULT1['id']}/comments"
    )
    assert script_session.request_history[4].request.url.path == "/api/v3/gtiwidget"
    assert script_session.request_history[4].request.params.get("theme")[0] == "dark"
    assert (
        script_session.request_history[5].request.url.path
        == common_responses.WIDGET_PATH_URL + "/summary"
    )
    assert (
        script_session.request_history[6].request.url.path
        == f"/api/v3/urls/{ENTITY_URL_RESULT2['id']}/comments"
    )
    assert script_session.request_history[7].request.url.path == "/api/v3/gtiwidget"
    assert script_session.request_history[7].request.params.get("theme")[0] == "dark"
    assert (
        script_session.request_history[8].request.url.path
        == common_responses.WIDGET_PATH_URL + "/summary"
    )

    assert action_output.results == ActionOutput(
        output_message=SUCCESS_URL_ENTITIES_MESSAGE,
        result_value=True,
        execution_state=ExecutionState.COMPLETED,
        json_output=ActionJsonOutput(
            title="JsonResult",
            content="",
            type=None,
            is_for_entity=False,
            json_result=RESULT_URL_ENTITIES_RESPONSE,
        ),
        debug_output="",
    )


ENTITY_IP_IDENTIFIER = "8.8.8.8"

SUCCESS_IP_ENTITY_MESSAGE = (
    "Successfully enriched the following entities using  "
    f"Google Threat Intelligence: \n {ENTITY_IP_IDENTIFIER} \n"
)

ENTITY_RESULT = common_responses.NON_MALICIOUS_IP_RESPONSE.get("data")
ENTITY_RESULT.update(
    {
        "widget_link": common_responses.WIDGET_URL_RESPONSE["data"]["url"] + "/summary",
        "widget_html": get_compressed_html(EMPTY_ESCAPED_HTML_RESPONSE_WITH_FONTS),
        "is_risky": False,
        "execution_status": "success",
        "comments": common_responses.IP_ADDRESS_COMMENTS_RESPONSE["data"],
    }
)

RESULT_IP_ENTITY_RESPONSE = [
    {
        "Entity": f"{ENTITY_IP_IDENTIFIER}",
        "EntityResult": ENTITY_RESULT,
    }
]


@set_metadata(
    integration_config=INTEGRATION_CONFIG_NO_ASM,
    parameters=INPUT_PARAMETERS,
    entities=[create_entity(ENTITY_IP_IDENTIFIER, EntityTypesEnum.ADDRESS)],
)
def test_enrich_entities_ip(
    script_session: GoogleThreatIntelligenceSession,
    action_output: MockActionOutput,
    google_threat_intelligence_product: GoogleThreatIntelligenceProduct,
) -> None:
    set_is_first_run_to_true()

    google_threat_intelligence_product.add_ioc(
        ioc_identifier=ENTITY_IP_IDENTIFIER,
        response_type_json=common_responses.NON_MALICIOUS_IP_RESPONSE,
    )

    google_threat_intelligence_product.add_comments(
        ioc_identifier=ENTITY_IP_IDENTIFIER,
        response=common_responses.IP_ADDRESS_COMMENTS_RESPONSE,
    )
    enrich_entities.main()

    assert len(script_session.request_history) == 5
    assert script_session.request_history[0].request.url.path == "/api/v3/metadata"
    assert script_session.request_history[1].request.url.path.startswith(
        "/api/v3/ip_addresses/"
    )
    assert (
        script_session.request_history[2].request.url.path
        == f"/api/v3/ip_addresses/{ENTITY_IP_IDENTIFIER}/comments"
    )
    assert script_session.request_history[3].request.url.path == "/api/v3/gtiwidget"
    assert action_output.results == ActionOutput(
        output_message=SUCCESS_IP_ENTITY_MESSAGE,
        result_value=True,
        execution_state=ExecutionState.COMPLETED,
        json_output=ActionJsonOutput(
            title="JsonResult",
            content="",
            type=None,
            is_for_entity=False,
            json_result=RESULT_IP_ENTITY_RESPONSE,
        ),
        debug_output="",
    )


@set_metadata(
    integration_config=INTEGRATION_CONFIG_NO_ASM,
    parameters=INPUT_PARAMETERS,
    entities=[create_entity(ENTITY_IP_IDENTIFIER, EntityTypesEnum.ADDRESS)],
)
def test_check_actions_connectivity_for_non_asm(
    script_session: GoogleThreatIntelligenceSession,
    google_threat_intelligence_product: GoogleThreatIntelligenceProduct,
) -> None:
    set_is_first_run_to_true()

    google_threat_intelligence_product.add_ioc(
        ioc_identifier=ENTITY_IP_IDENTIFIER,
        response_type_json=common_responses.NON_MALICIOUS_IP_RESPONSE,
    )

    google_threat_intelligence_product.add_comments(
        ioc_identifier=ENTITY_IP_IDENTIFIER,
        response=common_responses.IP_ADDRESS_COMMENTS_RESPONSE,
    )
    enrich_entities.main()

    assert len(script_session.request_history) == 5
    assert script_session.request_history[0].request.url.path == "/api/v3/metadata"


@set_metadata(
    integration_config=INTEGRATION_CONFIG_NO_ASM,
    parameters={**INPUT_PARAMETERS, "Widget Theme": "Light"},
    entities=[create_entity(ENTITY_IP_IDENTIFIER, EntityTypesEnum.ADDRESS)],
)
def test_enrich_entities_light_theme(
    script_session: GoogleThreatIntelligenceSession,
    google_threat_intelligence_product: GoogleThreatIntelligenceProduct,
) -> None:
    set_is_first_run_to_true()

    google_threat_intelligence_product.add_ioc(
        ioc_identifier=ENTITY_IP_IDENTIFIER,
        response_type_json=common_responses.NON_MALICIOUS_IP_RESPONSE,
    )

    google_threat_intelligence_product.add_comments(
        ioc_identifier=ENTITY_IP_IDENTIFIER,
        response=common_responses.IP_ADDRESS_COMMENTS_RESPONSE,
    )
    enrich_entities.main()

    assert len(script_session.request_history) == 5

    assert script_session.request_history[3].request.url.path == "/api/v3/gtiwidget"
    assert script_session.request_history[3].request.params.get("theme")[0] == "light"
    assert script_session.request_history[3].request.params.get("fg1")[0] == "4f5064"
    assert script_session.request_history[3].request.params.get("bg1")[0] == "ffffff"
    assert script_session.request_history[3].request.params.get("bg2")[0] == "f4f5fa"
    assert script_session.request_history[3].request.params.get("bd1")[0] == "d2d7e9"


ENTITY_CHILDHASH_IDENTIFIER = "c60d529a802046e447eadbae5c6aaf9bbf746322"
SUCCESS_CHILDHASH_ENTITY_MESSAGE = (
    "Successfully enriched the following entities using  "
    f"Google Threat Intelligence: \n {ENTITY_CHILDHASH_IDENTIFIER} \n"
)


@set_metadata(
    integration_config=INTEGRATION_CONFIG_NO_ASM,
    parameters={**INPUT_PARAMETERS, "Retrieve Comments": False},
    entities=[
        create_entity(
            ENTITY_CHILDHASH_IDENTIFIER, EntityTypesEnum.CHILD_HASH
        )
    ],
)
def test_enrich_entities_childhash(
    script_session: GoogleThreatIntelligenceSession,
    action_output: MockActionOutput,
    google_threat_intelligence_product: GoogleThreatIntelligenceProduct,
) -> None:
    set_is_first_run_to_true()

    google_threat_intelligence_product.add_ioc(
        ioc_identifier=ENTITY_CHILDHASH_IDENTIFIER,
        response_type_json=common_responses.NON_MALICIOUS_FILE_HASH_RESPONSE,
    )
    enrich_entities.main()

    assert action_output.results.result_value is True
    assert SUCCESS_CHILDHASH_ENTITY_MESSAGE in action_output.results.output_message


ENTITY_PARENTHASH_IDENTIFIER = "791d0fa941c37457973f04d12263d01ca5c480e5bfc795f025e79ac96e025af5"
SUCCESS_PARENTHASH_ENTITY_MESSAGE = (
    "Successfully enriched the following entities using  "
    f"Google Threat Intelligence: \n {ENTITY_PARENTHASH_IDENTIFIER} \n"
)


@set_metadata(
    integration_config=INTEGRATION_CONFIG_NO_ASM,
    parameters={**INPUT_PARAMETERS, "Retrieve Comments": False},
    entities=[
        create_entity(
            ENTITY_PARENTHASH_IDENTIFIER, EntityTypesEnum.PARENT_HASH
        )
    ],
)
def test_enrich_entities_parenthash(
    script_session: GoogleThreatIntelligenceSession,
    action_output: MockActionOutput,
    google_threat_intelligence_product: GoogleThreatIntelligenceProduct,
) -> None:
    set_is_first_run_to_true()

    google_threat_intelligence_product.add_ioc(
        ioc_identifier=ENTITY_PARENTHASH_IDENTIFIER,
        response_type_json=common_responses.NON_MALICIOUS_FILE_HASH_RESPONSE,
    )
    enrich_entities.main()

    assert action_output.results.result_value is True
    assert SUCCESS_PARENTHASH_ENTITY_MESSAGE in action_output.results.output_message

