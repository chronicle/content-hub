from __future__ import annotations

import copy
import json
from typing import TYPE_CHECKING

from TIPCommon.base.action import ExecutionState

from google_threat_intelligence.actions import submit_file
from google_threat_intelligence.tests.responses.api import common_responses
from integration_testing.common import set_is_first_run_to_true, set_is_first_run_to_false
from integration_testing.set_meta import set_metadata

if TYPE_CHECKING:
    from google_threat_intelligence.tests.core.product import GoogleThreatIntelligenceProduct
    from google_threat_intelligence.tests.core.session import GoogleThreatIntelligenceSession
    from integration_testing.platform.script_output import MockActionOutput

INTEGRATION_CONFIG_NO_ASM = {
    "API Root": "https://www.virustotal.com",
    "API Key": "TEST",
    "ASM Project Name": "",
    "Verify SSL": True,
}

FILE_PATH = "/opt/siemplify/private_test.txt"
ANALYSIS_ID = "analysis1"
FILE_HASH = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"

COMPLETED_ANALYSIS_RESPONSE = {
    "data": {"attributes": {"status": "completed"}},
    "meta": {"file_info": {"sha256": FILE_HASH}},
}

BASE_PARAMETERS = {
    "File Paths": FILE_PATH,
    "Fetch MITRE Details": False,
    "Check Hash First": False,
    "GTI Score": 60,
    "Resubmit After (Days)": 30,
    "Lowest MITRE Technique Severity": "Medium",
    "Retrieve Comments": True,
    "Max Comments To Return": 10,
    "additional_data": json.dumps(
        {
            "analysis_ids": {FILE_PATH: ANALYSIS_ID},
            "files_hashes": {},
            "successful_files": [FILE_PATH],
            "failed_entities": [],
        }
    ),
}


@set_metadata(integration_config=INTEGRATION_CONFIG_NO_ASM, parameters={**BASE_PARAMETERS, "Private Submission": True})
def test_submit_file_private_submission_skips_comments_consecutive_run(
    script_session: GoogleThreatIntelligenceSession,
    action_output: MockActionOutput,
    google_threat_intelligence_product: GoogleThreatIntelligenceProduct,
) -> None:
    set_is_first_run_to_false()
    google_threat_intelligence_product.add_analysis(analysis_id=ANALYSIS_ID, response=COMPLETED_ANALYSIS_RESPONSE)
    google_threat_intelligence_product.add_ioc(
        ioc_identifier=FILE_HASH,
        response_type_json=copy.deepcopy(common_responses.NON_MALICIOUS_FILE_HASH_RESPONSE),
    )

    submit_file.main()

    assert len(script_session.request_history) == 3
    assert script_session.request_history[0].request.url.path == "/api/v3/metadata"
    assert (
        script_session.request_history[1].request.url.path
        == f"/api/v3/private/analyses/{ANALYSIS_ID}"
    )
    assert (
        script_session.request_history[2].request.url.path
        == f"/api/v3/private/files/{FILE_HASH}"
    )
    assert action_output.results.execution_state == ExecutionState.COMPLETED
    assert action_output.results.result_value is True
    assert (
        "Successfully returned details about the following files"
        in action_output.results.output_message
    )
    assert (
        action_output.results.json_output.json_result[0]["EntityResult"][
            "execution_status"
        ]
        == "success"
    )
    assert (
        "comments"
        not in action_output.results.json_output.json_result[0]["EntityResult"]
    )


@set_metadata(integration_config=INTEGRATION_CONFIG_NO_ASM, parameters={**BASE_PARAMETERS, "Private Submission": False})
def test_submit_file_public_submission_retrieves_comments_consecutive_run(
    script_session: GoogleThreatIntelligenceSession,
    action_output: MockActionOutput,
    google_threat_intelligence_product: GoogleThreatIntelligenceProduct,
) -> None:
    set_is_first_run_to_false()
    google_threat_intelligence_product.add_analysis(analysis_id=ANALYSIS_ID, response=COMPLETED_ANALYSIS_RESPONSE)
    google_threat_intelligence_product.add_ioc(
        ioc_identifier=FILE_HASH,
        response_type_json=copy.deepcopy(common_responses.NON_MALICIOUS_FILE_HASH_RESPONSE),
    )
    google_threat_intelligence_product.add_comments(
        ioc_identifier=FILE_HASH,
        response=common_responses.URL_ADDRESS_COMMENTS_RESPONSE,
    )

    submit_file.main()

    assert len(script_session.request_history) == 4
    assert script_session.request_history[0].request.url.path == "/api/v3/metadata"
    assert (
        script_session.request_history[1].request.url.path
        == f"/api/v3/analyses/{ANALYSIS_ID}"
    )
    assert (
        script_session.request_history[2].request.url.path
        == f"/api/v3/files/{FILE_HASH}"
    )
    assert (
        script_session.request_history[3].request.url.path
        == f"/api/v3/files/{FILE_HASH}/comments"
    )
    assert action_output.results.execution_state == ExecutionState.COMPLETED
    assert action_output.results.result_value is True
    assert (
        action_output.results.json_output.json_result[0]["EntityResult"]["comments"]
        == common_responses.URL_ADDRESS_COMMENTS_RESPONSE["data"]
    )


@set_metadata(integration_config=INTEGRATION_CONFIG_NO_ASM, parameters={**BASE_PARAMETERS, "Private Submission": False})
def test_submit_file_public_submission_comments_not_found_does_not_fail_action(
    script_session: GoogleThreatIntelligenceSession,
    action_output: MockActionOutput,
    google_threat_intelligence_product: GoogleThreatIntelligenceProduct,
) -> None:
    set_is_first_run_to_false()
    google_threat_intelligence_product.add_analysis(analysis_id=ANALYSIS_ID, response=COMPLETED_ANALYSIS_RESPONSE)
    google_threat_intelligence_product.add_ioc(
        ioc_identifier=FILE_HASH,
        response_type_json=copy.deepcopy(common_responses.NON_MALICIOUS_FILE_HASH_RESPONSE),
    )

    submit_file.main()

    assert len(script_session.request_history) == 4
    assert (
        script_session.request_history[3].request.url.path
        == f"/api/v3/files/{FILE_HASH}/comments"
    )
    assert action_output.results.execution_state == ExecutionState.COMPLETED
    assert action_output.results.result_value is True
    assert (
        "Successfully returned details about the following files"
        in action_output.results.output_message
    )
    assert (
        action_output.results.json_output.json_result[0]["EntityResult"][
            "execution_status"
        ]
        == "success"
    )
