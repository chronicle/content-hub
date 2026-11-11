from __future__ import annotations

import json

from soar_sdk.SiemplifyUtils import unix_now
from TIPCommon.base.action import EntityTypesEnum, ExecutionState
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

from google_threat_intelligence.actions.private_submit_url import (
    PrivateSubmitUrl,
)

INTEGRATION_CONFIG_NO_ASM = {
    "API Root": "https://www.virustotal.com",
    "API Key": "TEST",
    "ASM Project Name": "",
    "Verify SSL": True,
}


def delay_async_timeout(action):
    action.soar_action.async_total_duration_deadline = unix_now() + 100000


@set_metadata(
    integration_config=INTEGRATION_CONFIG_NO_ASM,
    parameters={
        "URL": "https://example1.com, https://example2.com",
        "Check Existing Submissions First": True,
        "Resubmit After (Days)": "100000000",  # So it won`t try to resubmit
    },
    entities=[
        create_entity("https://example.com", EntityTypesEnum.URL),
        create_entity("8.8.8.8", EntityTypesEnum.ADDRESS),
        create_entity("example", EntityTypesEnum.HOST_NAME),
        create_entity("example.com", EntityTypesEnum.DOMAIN),
        create_entity("filehash", EntityTypesEnum.FILE_HASH),
    ],
)
def test_submit_private_url_first_run_should_call_public_api(
    script_session: GoogleThreatIntelligenceSession,
    action_output: MockActionOutput,
    google_threat_intelligence_product: GoogleThreatIntelligenceProduct,
):
    set_is_first_run_to_true()
    google_threat_intelligence_product.add_ioc(
        ioc_identifier="HTTPS://EXAMPLE.COM",
        response_type_json=common_responses.MALICIOUS_URL_RESPONSE,
    )
    google_threat_intelligence_product.add_ioc(
        ioc_identifier="https://example1.com",
        response_type_json=common_responses.NON_MALICIOUS_URL_RESPONSE,
    )
    google_threat_intelligence_product.add_ioc(
        ioc_identifier="https://example2.com",
        response_type_json=common_responses.NON_MALICIOUS_URL_RESPONSE,
    )
    action = PrivateSubmitUrl("PRIVATE_SUBMIT_URL_SCRIPT_NAME")
    delay_async_timeout(action)
    action.run()

    assert len(script_session.request_history) == 4
    assert (
        script_session.request_history[0].request.url.path
        == "/api/v3/metadata"
    )
    assert (
        script_session.request_history[1].request.url.path
        == "/api/v3/urls/aHR0cHM6Ly9leGFtcGxlMS5jb20"  # example1
    )
    assert (
        script_session.request_history[2].request.url.path
        == "/api/v3/urls/aHR0cHM6Ly9leGFtcGxlMi5jb20"  # example2
    )
    assert (
        script_session.request_history[3].request.url.path
        == "/api/v3/urls/SFRUUFM6Ly9FWEFNUExFLkNPTQ"  # example
    )

    assert action_output.results.execution_state == ExecutionState.COMPLETED


@set_metadata(
    integration_config=INTEGRATION_CONFIG_NO_ASM,
    parameters={
        "URL": "https://example1.com, https://example2.com",
        "Check Existing Submissions First": False,
        "Resubmit After (Days)": "30",
    },
    entities=[
        create_entity("https://example.com", EntityTypesEnum.URL),
    ],
)
def test_submit_private_url_only_private_submit_first_run(
    script_session: GoogleThreatIntelligenceSession,
    action_output: MockActionOutput,
    google_threat_intelligence_product: GoogleThreatIntelligenceProduct,
):
    set_is_first_run_to_true()
    google_threat_intelligence_product.add_ioc(
        ioc_identifier="HTTPS://EXAMPLE.COM",
        response_type_json=common_responses.MALICIOUS_PRIVATE_URL_RESPONSE,
    )
    google_threat_intelligence_product.add_ioc(
        ioc_identifier="https://example1.com",
        response_type_json=common_responses.NON_MALICIOUS_PRIVATE_URL_RESPONSE,
    )
    google_threat_intelligence_product.add_ioc(
        ioc_identifier="https://example2.com",
        response_type_json=common_responses.NON_MALICIOUS_PRIVATE_URL_RESPONSE,
    )
    action = PrivateSubmitUrl("PRIVATE_SUBMIT_URL_SCRIPT_NAME")
    delay_async_timeout(action)
    action.run()

    assert len(script_session.request_history) == 4
    assert (
        script_session.request_history[0].request.url.path
        == "/api/v3/metadata"
    )
    assert script_session.request_history[1].request.url.path == "/api/v3/private/urls"
    assert script_session.request_history[2].request.url.path == "/api/v3/private/urls"
    assert script_session.request_history[3].request.url.path == "/api/v3/private/urls"

    assert action_output.results.execution_state == ExecutionState.IN_PROGRESS


@set_metadata(
    integration_config=INTEGRATION_CONFIG_NO_ASM,
    parameters={
        "URL": "https://example1.com, https://example2.com",
        "Check Existing Submissions First": False,
        "Resubmit After (Days)": "30",
        "additional_data": json.dumps(
            {
                "https://example1.com": {
                    "identifier": "aHR0cHM6Ly9leGFtcGxlMS5jb20",
                    "state": "SUBMITTED",
                    "_last_result": None,
                    "analysis_id": "id1",
                    "url": "https://example1.com",
                },
                "https://example2.com": {
                    "identifier": "aHR0cHM6Ly9leGFtcGxlMi5jb20",
                    "state": "SUBMITTED",
                    "_last_result": None,
                    "analysis_id": "id2",
                    "url": "https://example2.com",
                },
                "HTTPS://EXAMPLE.COM": {
                    "identifier": "SFRUUFM6Ly9FWEFNUExFLkNPTQ",
                    "state": "SUBMITTED",
                    "_last_result": None,
                    "analysis_id": "id3",
                    "url": "HTTPS://EXAMPLE.COM",
                },
            }
        ),
    },
    entities=[
        create_entity("https://example.com", EntityTypesEnum.URL),
    ],
)
def test_submit_private_url_only_private_submit_consecutive_run(
    script_session: GoogleThreatIntelligenceSession,
    action_output: MockActionOutput,
    google_threat_intelligence_product: GoogleThreatIntelligenceProduct,
):
    set_is_first_run_to_false()
    google_threat_intelligence_product.add_ioc(
        ioc_identifier="HTTPS://EXAMPLE.COM",
        response_type_json=common_responses.MALICIOUS_PRIVATE_URL_RESPONSE,
    )
    google_threat_intelligence_product.add_ioc(
        ioc_identifier="https://example1.com",
        response_type_json=common_responses.NON_MALICIOUS_PRIVATE_URL_RESPONSE,
    )
    google_threat_intelligence_product.add_ioc(
        ioc_identifier="https://example2.com",
        response_type_json=common_responses.NON_MALICIOUS_PRIVATE_URL_RESPONSE,
    )
    action = PrivateSubmitUrl("PRIVATE_SUBMIT_URL_SCRIPT_NAME")
    delay_async_timeout(action)
    action.run()

    assert len(script_session.request_history) == 7
    assert (
        script_session.request_history[0].request.url.path
        == "/api/v3/metadata"
    )
    assert (
        script_session.request_history[1].request.url.path
        == "/api/v3/private/analyses/id1"  # example1
    )
    assert (
        script_session.request_history[2].request.url.path
        == "/api/v3/private/urls/aHR0cHM6Ly9leGFtcGxlMS5jb20"  # example1
    )
    assert (
        script_session.request_history[3].request.url.path
        == "/api/v3/private/analyses/id2"  # example2
    )
    assert (
        script_session.request_history[4].request.url.path
        == "/api/v3/private/urls/aHR0cHM6Ly9leGFtcGxlMi5jb20"  # example2
    )
    assert (
        script_session.request_history[5].request.url.path
        == "/api/v3/private/analyses/id3"  # example
    )
    assert (
        script_session.request_history[6].request.url.path
        == "/api/v3/private/urls/SFRUUFM6Ly9FWEFNUExFLkNPTQ"  # example
    )
    assert action_output.results.execution_state == ExecutionState.COMPLETED
