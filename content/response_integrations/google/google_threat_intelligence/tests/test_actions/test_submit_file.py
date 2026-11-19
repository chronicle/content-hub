# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import annotations

import copy
import json
from typing import TYPE_CHECKING

import pytest
from soar_sdk.SiemplifyUtils import unix_now
from TIPCommon.base.action import ExecutionState

from google_threat_intelligence.actions import submit_file
from google_threat_intelligence.tests.responses.api import common_responses
from integration_testing.common import set_is_first_run_to_false, set_is_first_run_to_true
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
SECOND_FILE_PATH = "/opt/siemplify/second_test.txt"
ANALYSIS_ID = "analysis1"
SECOND_ANALYSIS_ID = "analysis2"
FILE_HASH = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"

TRANSIENT_503_ERROR_RESPONSE = {
    "error": {"code": "TransientError", "message": "Concurrently processing matching analysis."}
}

BAD_REQUEST_400_ERROR_RESPONSE = {"error": {"code": "BadRequestError", "message": "Invalid file upload payload."}}

COMPLETED_ANALYSIS_RESPONSE = {
    "data": {"attributes": {"status": "completed"}},
    "meta": {"file_info": {"sha256": FILE_HASH}},
}

FIRST_RUN_PARAMETERS = {
    "File Paths": FILE_PATH,
    "Private Submission": False,
    "Fetch MITRE Details": False,
    "Check Hash First": False,
    "GTI Score": 60,
    "Resubmit After (Days)": 30,
    "Lowest MITRE Technique Severity": "Medium",
    "Retrieve Comments": False,
    "Max Comments To Return": 10,
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


@set_metadata(integration_config=INTEGRATION_CONFIG_NO_ASM, parameters=FIRST_RUN_PARAMETERS)
def test_submit_file_first_run_503_error_queues_pending_upload(
    monkeypatch: pytest.MonkeyPatch,
    script_session: GoogleThreatIntelligenceSession,
    action_output: MockActionOutput,
    google_threat_intelligence_product: GoogleThreatIntelligenceProduct,
) -> None:
    """Scenario 1: First run 503 returns IN_PROGRESS with file in pending_uploads."""
    set_is_first_run_to_true()
    monkeypatch.setattr(submit_file.SubmitFile, "get_file_content", lambda *_, **__: b"sample content")
    google_threat_intelligence_product.set_file_upload_response(content=TRANSIENT_503_ERROR_RESPONSE, status_code=503)

    submit_file.main()

    assert len(script_session.request_history) == 3
    assert script_session.request_history[0].request.url.path == "/api/v3/metadata"
    assert script_session.request_history[1].request.url.path == "/api/v3/files/upload_url"
    assert script_session.request_history[2].request.url.path == "/_ah/upload/test_upload_url"
    assert action_output.results.execution_state == ExecutionState.IN_PROGRESS
    assert isinstance(action_output.results.result_value, str)
    state_data = json.loads(action_output.results.result_value)
    assert state_data["analysis_ids"] == {}
    assert state_data["pending_uploads"][FILE_PATH]["attempts"] == 1
    assert "503" in state_data["pending_uploads"][FILE_PATH]["last_error"]
    assert "TransientError" in state_data["pending_uploads"][FILE_PATH]["last_error"]
    assert "Retry is pending" in action_output.results.output_message


@pytest.mark.parametrize("is_private", [False, True])
def test_submit_file_retry_pending_upload_succeeds(
    monkeypatch: pytest.MonkeyPatch,
    script_session: GoogleThreatIntelligenceSession,
    action_output: MockActionOutput,
    google_threat_intelligence_product: GoogleThreatIntelligenceProduct,
    is_private: bool,
) -> None:
    """Scenario 2: Next run 200 sets analysis_ids and clears pending_uploads."""
    set_is_first_run_to_false()
    monkeypatch.setattr(submit_file.SubmitFile, "get_file_content", lambda *_, **__: b"sample content")
    google_threat_intelligence_product.set_file_upload_response(content={"data": {"id": ANALYSIS_ID}}, status_code=200)
    pending_state = {"pending_uploads": {FILE_PATH: {"attempts": 1, "last_error": "503 TransientError"}}}

    set_metadata(
        integration_config=INTEGRATION_CONFIG_NO_ASM,
        parameters={
            **FIRST_RUN_PARAMETERS,
            "Private Submission": is_private,
            "additional_data": json.dumps(pending_state),
        },
    )(submit_file.main)()

    expected_upload_url_path = "/api/v3/private/files/upload_url" if is_private else "/api/v3/files/upload_url"
    expected_post_path = "/_ah/upload/test_private_upload_url" if is_private else "/_ah/upload/test_upload_url"
    assert len(script_session.request_history) == 3
    assert script_session.request_history[1].request.url.path == expected_upload_url_path
    assert script_session.request_history[2].request.url.path == expected_post_path
    assert action_output.results.execution_state == ExecutionState.IN_PROGRESS
    state_data = json.loads(action_output.results.result_value)
    assert state_data["analysis_ids"] == {FILE_PATH: ANALYSIS_ID}
    assert state_data["pending_uploads"] == {}
    assert state_data["successful_files"] == [FILE_PATH]


@set_metadata(
    integration_config=INTEGRATION_CONFIG_NO_ASM,
    parameters={
        **FIRST_RUN_PARAMETERS,
        "additional_data": json.dumps(
            {"pending_uploads": {FILE_PATH: {"attempts": 1, "last_error": "503 TransientError"}}}
        ),
    },
)
def test_submit_file_retry_pending_upload_503_again_increments_attempts(
    monkeypatch: pytest.MonkeyPatch,
    action_output: MockActionOutput,
    google_threat_intelligence_product: GoogleThreatIntelligenceProduct,
) -> None:
    """Scenario 3: Next run 503 below limit keeps file pending and increments attempts."""
    set_is_first_run_to_false()
    monkeypatch.setattr(submit_file.SubmitFile, "get_file_content", lambda *_, **__: b"sample content")
    google_threat_intelligence_product.set_file_upload_response(content=TRANSIENT_503_ERROR_RESPONSE, status_code=503)

    submit_file.main()

    assert action_output.results.execution_state == ExecutionState.IN_PROGRESS
    state_data = json.loads(action_output.results.result_value)
    assert state_data["pending_uploads"][FILE_PATH]["attempts"] == 2
    assert "TransientError" in state_data["pending_uploads"][FILE_PATH]["last_error"]


@set_metadata(
    integration_config=INTEGRATION_CONFIG_NO_ASM,
    parameters={
        **FIRST_RUN_PARAMETERS,
        "File Paths": f"{FILE_PATH},{SECOND_FILE_PATH}",
        "additional_data": json.dumps(
            {
                "analysis_ids": {FILE_PATH: ANALYSIS_ID},
                "successful_files": [FILE_PATH],
                "pending_uploads": {
                    SECOND_FILE_PATH: {"attempts": 4, "last_error": "An error occurred: 503 TransientError"}
                },
            }
        ),
    },
)
def test_submit_file_retry_limit_reached_fails_file_and_finalizes_others(
    monkeypatch: pytest.MonkeyPatch,
    action_output: MockActionOutput,
    google_threat_intelligence_product: GoogleThreatIntelligenceProduct,
) -> None:
    """Scenario 4a: Attempt limit reached fails pending file with 503 text and finalizes others."""
    set_is_first_run_to_false()
    monkeypatch.setattr(submit_file.SubmitFile, "get_file_content", lambda *_, **__: b"sample content")
    google_threat_intelligence_product.set_file_upload_response(content=TRANSIENT_503_ERROR_RESPONSE, status_code=503)
    google_threat_intelligence_product.add_analysis(analysis_id=ANALYSIS_ID, response=COMPLETED_ANALYSIS_RESPONSE)
    google_threat_intelligence_product.add_ioc(
        ioc_identifier=FILE_HASH,
        response_type_json=copy.deepcopy(common_responses.NON_MALICIOUS_FILE_HASH_RESPONSE),
    )

    submit_file.main()

    assert action_output.results.execution_state == ExecutionState.COMPLETED
    assert action_output.results.result_value is True
    assert "503" in action_output.results.output_message
    assert "TransientError" in action_output.results.output_message
    results_by_entity = {item["Entity"]: item["EntityResult"] for item in action_output.results.json_output.json_result}
    assert results_by_entity[FILE_PATH]["execution_status"] == "success"
    assert "503" in results_by_entity[SECOND_FILE_PATH]["execution_status"]
    assert "TransientError" in results_by_entity[SECOND_FILE_PATH]["execution_status"]


@set_metadata(
    integration_config=INTEGRATION_CONFIG_NO_ASM,
    input_context={"async_total_duration_deadline": 1},
    parameters={
        **FIRST_RUN_PARAMETERS,
        "additional_data": json.dumps(
            {"pending_uploads": {FILE_PATH: {"attempts": 1, "last_error": "An error occurred: 503 TransientError"}}},
        ),
    },
)
def test_submit_file_approaching_deadline_fails_pending_file_with_503_text(action_output: MockActionOutput) -> None:
    """Scenario 4b: Approaching async deadline fails pending file with real 503 text."""
    set_is_first_run_to_false()

    submit_file.main()

    assert action_output.results.execution_state == ExecutionState.FAILED
    assert action_output.results.result_value is False
    assert "503" in action_output.results.output_message
    assert "TransientError" in action_output.results.output_message


@pytest.mark.parametrize(("seconds_left", "expected_uploads"), [(30, 0), (120, 1)])
def test_submit_file_retry_respects_async_deadline_margin(
    monkeypatch: pytest.MonkeyPatch,
    script_session: GoogleThreatIntelligenceSession,
    google_threat_intelligence_product: GoogleThreatIntelligenceProduct,
    seconds_left: int,
    expected_uploads: int,
) -> None:
    """Retry a pending upload only when the async deadline is more than 60 seconds away."""
    set_is_first_run_to_false()
    monkeypatch.setattr(submit_file.SubmitFile, "get_file_content", lambda *_, **__: b"sample content")
    google_threat_intelligence_product.set_file_upload_response(content={"data": {"id": ANALYSIS_ID}}, status_code=200)
    pending_state = {"pending_uploads": {FILE_PATH: {"attempts": 1, "last_error": "503 TransientError"}}}
    set_metadata(
        integration_config=INTEGRATION_CONFIG_NO_ASM,
        input_context={"async_total_duration_deadline": unix_now() + seconds_left * 1000},
        parameters={**FIRST_RUN_PARAMETERS, "additional_data": json.dumps(pending_state)},
    )(submit_file.main)()

    uploads = [call for call in script_session.request_history if call.request.url.path.startswith("/_ah/upload/")]
    assert len(uploads) == expected_uploads


def test_submit_file_partial_503_saves_first_file_and_retries_only_second_file(
    monkeypatch: pytest.MonkeyPatch,
    script_session: GoogleThreatIntelligenceSession,
    action_output: MockActionOutput,
    google_threat_intelligence_product: GoogleThreatIntelligenceProduct,
) -> None:
    """Scenario 5: File A gets 200, File B gets 503; next run uploads only B."""
    set_is_first_run_to_true()
    monkeypatch.setattr(submit_file.SubmitFile, "get_file_content", lambda *_, **__: b"sample content")
    google_threat_intelligence_product.set_file_upload_response(
        [
            ({"data": {"id": ANALYSIS_ID}}, 200),
            (TRANSIENT_503_ERROR_RESPONSE, 503),
            ({"data": {"id": SECOND_ANALYSIS_ID}}, 200),
        ]
    )
    google_threat_intelligence_product.add_analysis(
        analysis_id=ANALYSIS_ID,
        response={"data": {"attributes": {"status": "queued"}}},
    )

    two_file_params = {**FIRST_RUN_PARAMETERS, "File Paths": f"{FILE_PATH},{SECOND_FILE_PATH}"}
    set_metadata(integration_config=INTEGRATION_CONFIG_NO_ASM, parameters=two_file_params)(submit_file.main)()

    assert action_output.results.execution_state == ExecutionState.IN_PROGRESS
    saved_result_value = action_output.results.result_value
    first_run_state = json.loads(saved_result_value)
    assert first_run_state["analysis_ids"] == {FILE_PATH: ANALYSIS_ID}
    assert list(first_run_state["pending_uploads"].keys()) == [SECOND_FILE_PATH]

    script_session.request_history.clear()
    action_output.flush()
    set_is_first_run_to_false()
    set_metadata(
        integration_config=INTEGRATION_CONFIG_NO_ASM,
        parameters={**two_file_params, "additional_data": saved_result_value},
    )(submit_file.main)()

    uploads = [call for call in script_session.request_history if call.request.url.path.startswith("/_ah/upload/")]
    assert [call.request.url.path for call in uploads] == ["/_ah/upload/test_upload_url"]
    second_run_state = json.loads(action_output.results.result_value)
    assert second_run_state["analysis_ids"] == {SECOND_FILE_PATH: SECOND_ANALYSIS_ID, FILE_PATH: ANALYSIS_ID}
    assert second_run_state["pending_uploads"] == {}


@set_metadata(
    integration_config=INTEGRATION_CONFIG_NO_ASM,
    parameters={**FIRST_RUN_PARAMETERS, "File Paths": f"{FILE_PATH},{SECOND_FILE_PATH}"},
)
def test_submit_file_400_marks_file_failed_and_other_file_continues(
    monkeypatch: pytest.MonkeyPatch,
    action_output: MockActionOutput,
    google_threat_intelligence_product: GoogleThreatIntelligenceProduct,
) -> None:
    """Scenario 6: One file gets 400 and is marked failed while the other continues."""
    set_is_first_run_to_true()
    monkeypatch.setattr(submit_file.SubmitFile, "get_file_content", lambda *_, **__: b"sample content")
    google_threat_intelligence_product.set_file_upload_response(
        [(BAD_REQUEST_400_ERROR_RESPONSE, 400), ({"data": {"id": SECOND_ANALYSIS_ID}}, 200)]
    )

    submit_file.main()

    assert action_output.results.execution_state == ExecutionState.IN_PROGRESS
    state_data = json.loads(action_output.results.result_value)
    assert state_data["failed_entities"] == [FILE_PATH]
    assert "BadRequestError" in state_data["entities_existing_data"][FILE_PATH]["execution_status"]
    assert state_data["pending_uploads"] == {}
    assert state_data["analysis_ids"] == {SECOND_FILE_PATH: SECOND_ANALYSIS_ID}


@pytest.mark.parametrize("status_code", [429, 504])
def test_submit_file_429_and_504_handled_as_transient_errors(
    monkeypatch: pytest.MonkeyPatch,
    action_output: MockActionOutput,
    google_threat_intelligence_product: GoogleThreatIntelligenceProduct,
    status_code: int,
) -> None:
    """Scenario 7: 429 and 504 are queued in pending_uploads like 503."""
    set_is_first_run_to_true()
    monkeypatch.setattr(submit_file.SubmitFile, "get_file_content", lambda *_, **__: b"sample content")
    google_threat_intelligence_product.set_file_upload_response(
        content={"error": {"code": "TransientError", "message": "Temporary error"}},
        status_code=status_code,
    )

    set_metadata(integration_config=INTEGRATION_CONFIG_NO_ASM, parameters=FIRST_RUN_PARAMETERS)(submit_file.main)()

    assert action_output.results.execution_state == ExecutionState.IN_PROGRESS
    state_data = json.loads(action_output.results.result_value)
    assert state_data["pending_uploads"][FILE_PATH]["attempts"] == 1
    assert str(status_code) in state_data["pending_uploads"][FILE_PATH]["last_error"]


@pytest.mark.parametrize("raw_additional_data", ["false", "true"])
def test_submit_file_non_dict_additional_data_resubmits_file(
    monkeypatch: pytest.MonkeyPatch,
    script_session: GoogleThreatIntelligenceSession,
    action_output: MockActionOutput,
    google_threat_intelligence_product: GoogleThreatIntelligenceProduct,
    raw_additional_data: str,
) -> None:
    """Scenario 8: additional_data='false' or 'true' is normalized and resubmits the file."""
    set_is_first_run_to_false()
    monkeypatch.setattr(submit_file.SubmitFile, "get_file_content", lambda *_, **__: b"sample content")
    google_threat_intelligence_product.set_file_upload_response(content={"data": {"id": ANALYSIS_ID}}, status_code=200)

    set_metadata(
        integration_config=INTEGRATION_CONFIG_NO_ASM,
        parameters={**FIRST_RUN_PARAMETERS, "additional_data": raw_additional_data},
    )(submit_file.main)()

    assert len(script_session.request_history) == 3
    assert action_output.results.execution_state == ExecutionState.IN_PROGRESS
    state_data = json.loads(action_output.results.result_value)
    assert state_data["analysis_ids"] == {FILE_PATH: ANALYSIS_ID}
    assert state_data["successful_files"] == [FILE_PATH]


def test_submit_file_external_url_downloads_and_submits_file(
    script_session: GoogleThreatIntelligenceSession,
    action_output: MockActionOutput,
    google_threat_intelligence_product: GoogleThreatIntelligenceProduct,
) -> None:
    """External URLs branch downloads the file and submits it for analysis."""
    set_is_first_run_to_true()
    external_url = "https://www.virustotal.com/api/v3/files/sample/download"
    google_threat_intelligence_product.set_file_upload_response(content={"data": {"id": ANALYSIS_ID}}, status_code=200)

    set_metadata(
        integration_config=INTEGRATION_CONFIG_NO_ASM,
        parameters={**FIRST_RUN_PARAMETERS, "File Paths": "", "External URLs": external_url},
    )(submit_file.main)()

    assert script_session.request_history[1].request.url.path == "/api/v3/files/sample/download"
    assert script_session.request_history[3].request.url.path == "/_ah/upload/test_upload_url"
    assert action_output.results.execution_state == ExecutionState.IN_PROGRESS
    state_data = json.loads(action_output.results.result_value)
    assert state_data["analysis_ids"] == {external_url: ANALYSIS_ID}
    assert state_data["successful_files"] == [external_url]


@set_metadata(
    integration_config=INTEGRATION_CONFIG_NO_ASM,
    parameters={**FIRST_RUN_PARAMETERS, "Check Hash First": True},
)
def test_submit_file_check_hash_first_known_hash_skips_upload(
    monkeypatch: pytest.MonkeyPatch,
    script_session: GoogleThreatIntelligenceSession,
    action_output: MockActionOutput,
    google_threat_intelligence_product: GoogleThreatIntelligenceProduct,
) -> None:
    """Check Hash First with a recent report skips upload and finalizes using the existing hash."""
    set_is_first_run_to_true()
    monkeypatch.setattr(submit_file.SubmitFile, "get_file_content", lambda *_, **__: b"")
    recent_report = copy.deepcopy(common_responses.NON_MALICIOUS_FILE_HASH_RESPONSE)
    recent_report["data"]["attributes"]["last_analysis_date"] = int(unix_now() / 1000)
    google_threat_intelligence_product.add_ioc(ioc_identifier=FILE_HASH, response_type_json=recent_report)

    submit_file.main()

    uploads = [call for call in script_session.request_history if call.request.url.path.startswith("/_ah/upload/")]
    assert len(uploads) == 0
    assert action_output.results.execution_state == ExecutionState.COMPLETED
    assert action_output.results.result_value is True


@set_metadata(
    integration_config=INTEGRATION_CONFIG_NO_ASM,
    parameters={**FIRST_RUN_PARAMETERS, "Check Hash First": True},
)
def test_submit_file_check_hash_first_outdated_report_uploads_again(
    monkeypatch: pytest.MonkeyPatch,
    script_session: GoogleThreatIntelligenceSession,
    action_output: MockActionOutput,
    google_threat_intelligence_product: GoogleThreatIntelligenceProduct,
) -> None:
    """Check Hash First with an outdated report uploads the file again."""
    set_is_first_run_to_true()
    monkeypatch.setattr(submit_file.SubmitFile, "get_file_content", lambda *_, **__: b"")
    outdated_report = copy.deepcopy(common_responses.NON_MALICIOUS_FILE_HASH_RESPONSE)
    outdated_report["data"]["attributes"]["last_analysis_date"] = 1
    google_threat_intelligence_product.add_ioc(ioc_identifier=FILE_HASH, response_type_json=outdated_report)
    google_threat_intelligence_product.set_file_upload_response(content={"data": {"id": ANALYSIS_ID}}, status_code=200)

    submit_file.main()

    uploads = [call for call in script_session.request_history if call.request.url.path.startswith("/_ah/upload/")]
    assert len(uploads) == 1
    assert action_output.results.execution_state == ExecutionState.IN_PROGRESS
    state_data = json.loads(action_output.results.result_value)
    assert state_data["analysis_ids"] == {FILE_PATH: ANALYSIS_ID}
