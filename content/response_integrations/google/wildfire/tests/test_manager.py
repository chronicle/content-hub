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

import re
import time

import pytest
import requests

from ..core.WildfireManager import (
    DEFAULT_API_ROOT,
    WildfireManager,
    WildfireManagerError,
    WildfireNotFoundError,
)

SAMPLE_MD5 = "44d88612fea8a8f36de82e1278abb02f"
SAMPLE_SHA256 = "275a021bbfb6489e54d471899f7db9d1663fc695ec2fe2a2c4538aabf651fd0f"
MOCK_XML_REPORT = """<wildfire version="2.0">
    <file_info>
        <md5>44d88612fea8a8f36de82e1278abb02f</md5>
        <malware>yes</malware>
        <type>PE</type>
    </file_info>
    <task_info>
        <report>Sample Task Report</report>
    </task_info>
</wildfire>"""


def test_init_with_api_key():
    mgr = WildfireManager(api_key="test-api-key")
    assert not mgr.is_scm
    assert mgr.api_key == "test-api-key"
    assert mgr.api_root == DEFAULT_API_ROOT


def test_init_with_scm():
    mgr = WildfireManager(
        client_id="test-client-id",
        client_secret="test-secret",
        tsg_id="1234567890",
    )
    assert mgr.is_scm
    assert mgr.client_id == "test-client-id"
    assert mgr.client_secret == "test-secret"
    assert mgr.tsg_id == "1234567890"


def test_init_missing_credentials():
    expected = (
        r"Either 'Api Key' or \('Client ID', 'Client Secret', and 'TSG ID'\) "
        r"must be provided for Palo Alto Wildfire authentication\."
    )
    with pytest.raises(WildfireManagerError, match=expected):
        WildfireManager()


def test_scm_get_token_success(mocker):
    mgr = WildfireManager(
        client_id="test-client-id",
        client_secret="test-secret",
        tsg_id="1234567890",
    )

    mock_resp = mocker.Mock()
    mock_resp.ok = True
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "access_token": "mock-bearer-token-xyz",
        "token_type": "Bearer",
        "expires_in": 900,
    }
    mocker.patch.object(mgr.session, "post", return_value=mock_resp)

    token = mgr.get_token()
    assert token == "mock-bearer-token-xyz"
    assert mgr._token == "mock-bearer-token-xyz"
    assert mgr._token_expires_at > time.time()

    # Second call should return cached token without requesting post
    mgr.session.post.reset_mock()
    cached_token = mgr.get_token()
    assert cached_token == "mock-bearer-token-xyz"
    mgr.session.post.assert_not_called()


def test_scm_get_token_failure(mocker):
    mgr = WildfireManager(
        client_id="test-client-id",
        client_secret="test-secret",
        tsg_id="1234567890",
    )

    mock_resp = mocker.Mock()
    mock_resp.ok = False
    mock_resp.status_code = 401
    mock_resp.text = "Unauthorized"
    mocker.patch.object(mgr.session, "post", return_value=mock_resp)

    with pytest.raises(WildfireManagerError, match="Authentication failed: HTTP 401"):
        mgr.get_token()


def test_scm_get_token_failure_json_error(mocker):
    mgr = WildfireManager(
        client_id="test-client-id",
        client_secret="test-secret",
        tsg_id="1234567890",
    )

    mock_resp = mocker.Mock()
    mock_resp.ok = False
    mock_resp.status_code = 401
    mock_resp.text = '{"error": "invalid_client", "error_description": "Client authentication failed"}'
    mock_resp.json.return_value = {
        "error": "invalid_client",
        "error_description": "Client authentication failed",
    }
    mocker.patch.object(mgr.session, "post", return_value=mock_resp)

    with pytest.raises(
        WildfireManagerError,
        match="Authentication failed: HTTP 401 - invalid_client: Client authentication failed",
    ):
        mgr.get_token()


def test_scm_get_token_invalid_expires_in_does_not_leak_token(mocker):
    mgr = WildfireManager(
        client_id="test-client-id",
        client_secret="test-secret",
        tsg_id="1234567890",
    )

    secret_token = "super-sensitive-bearer-token"
    mock_resp = mocker.Mock()
    mock_resp.ok = True
    mock_resp.status_code = 200
    mock_resp.text = f'{{"access_token": "{secret_token}", "expires_in": "invalid"}}'
    mock_resp.json.return_value = {
        "access_token": secret_token,
        "expires_in": "invalid",
    }
    mocker.patch.object(mgr.session, "post", return_value=mock_resp)

    with pytest.raises(WildfireManagerError, match="invalid 'expires_in'") as exc_info:
        mgr.get_token()

    assert secret_token not in str(exc_info.value)


def test_scm_get_token_missing_access_token(mocker):
    mgr = WildfireManager(
        client_id="test-client-id",
        client_secret="test-secret",
        tsg_id="1234567890",
    )

    mock_resp = mocker.Mock()
    mock_resp.ok = True
    mock_resp.status_code = 200
    mock_resp.text = '{"token_type": "Bearer"}'
    mock_resp.json.return_value = {"token_type": "Bearer"}
    mocker.patch.object(mgr.session, "post", return_value=mock_resp)

    with pytest.raises(WildfireManagerError, match="did not include an access token"):
        mgr.get_token()


def test_scm_get_token_not_configured():
    mgr = WildfireManager(api_key="my-secret-key")
    with pytest.raises(WildfireManagerError, match=r"SCM credentials are not configured on this instance\."):
        mgr.get_token()


def test_scm_get_token_connection_error(mocker):
    mgr = WildfireManager(
        client_id="test-client-id",
        client_secret="test-secret",
        tsg_id="1234567890",
    )
    mocker.patch.object(mgr.session, "post", side_effect=requests.exceptions.ConnectionError("DNS error"))

    with pytest.raises(WildfireManagerError, match=r"Failed to connect to authentication server \(.*\): DNS error"):
        mgr.get_token()


def test_scm_get_token_non_json_response(mocker):
    mgr = WildfireManager(
        client_id="test-client-id",
        client_secret="test-secret",
        tsg_id="1234567890",
    )
    mock_resp = mocker.Mock()
    mock_resp.ok = True
    mock_resp.status_code = 200
    mock_resp.json.side_effect = ValueError("No JSON")
    mocker.patch.object(mgr.session, "post", return_value=mock_resp)

    with pytest.raises(
        WildfireManagerError,
        match=r"Unexpected non-JSON token response from authentication server\.",
    ):
        mgr.get_token()


def test_get_sample_scm(mocker):
    mgr = WildfireManager(
        client_id="test-client-id",
        client_secret="test-secret",
        tsg_id="1234567890",
    )
    mocker.patch.object(mgr, "get_token", return_value="mock-token")

    mock_resp = mocker.Mock()
    mock_resp.ok = True
    mock_resp.status_code = 200
    mock_resp.text = ""
    mock_resp.content = b"PK\x03\x04test_sample_bytes"
    mock_resp.headers = {"Content-Disposition": 'attachment; filename="malware.tar"'}
    mocker.patch.object(mgr.session, "request", return_value=mock_resp)

    result = mgr.get_sample(SAMPLE_SHA256)
    assert result["filename"] == "malware.tar"
    assert result["content"] == b"PK\x03\x04test_sample_bytes"

    # Verify Authorization header and URL
    call_args = mgr.session.request.call_args
    assert call_args.kwargs["headers"]["Authorization"] == "Bearer mock-token"
    assert call_args.kwargs["data"]["hash"] == SAMPLE_SHA256
    assert "apikey" not in call_args.kwargs["data"]
    assert call_args.kwargs["url"] == f"{DEFAULT_API_ROOT}/publicapi/get/sample"


def test_get_sample_api_key(mocker):
    mgr = WildfireManager(api_key="my-secret-key")

    mock_resp = mocker.Mock()
    mock_resp.ok = True
    mock_resp.status_code = 200
    mock_resp.text = ""
    mock_resp.content = b"sample_bytes_123"
    mock_resp.headers = {}
    mocker.patch.object(mgr.session, "request", return_value=mock_resp)

    result = mgr.get_sample(SAMPLE_MD5)
    assert result["filename"] == f"{SAMPLE_MD5}.tar"
    assert result["content"] == b"sample_bytes_123"

    call_args = mgr.session.request.call_args
    assert "Authorization" not in call_args.kwargs["headers"]
    assert call_args.kwargs["data"]["apikey"] == "my-secret-key"
    assert call_args.kwargs["data"]["hash"] == SAMPLE_MD5


def test_get_sample_not_found(mocker):
    mgr = WildfireManager(api_key="my-secret-key")

    mock_resp = mocker.Mock()
    mock_resp.ok = False
    mock_resp.status_code = 404
    mock_resp.text = "HTTP Error 404: Not Found"
    mocker.patch.object(mgr.session, "request", return_value=mock_resp)

    with pytest.raises(WildfireNotFoundError, match=f"Sample is not available for {SAMPLE_MD5}"):
        mgr.get_sample(SAMPLE_MD5)


def test_get_sample_http_error_xml_and_plain(mocker):
    mgr = WildfireManager(api_key="my-secret-key")

    mock_xml = mocker.Mock()
    mock_xml.ok = False
    mock_xml.status_code = 403
    mock_xml.content = b"<wildfire><error><error-message>Invalid API key</error-message></error></wildfire>"
    mock_xml.text = "raw body"
    mocker.patch.object(mgr.session, "request", return_value=mock_xml)

    with pytest.raises(
        WildfireManagerError,
        match=(
            f"Unable to get sample of {SAMPLE_MD5}: "
            "Palo Alto Wildfire request failed with status code 403: Invalid API key"
        ),
    ) as exc_info:
        mgr.get_sample(SAMPLE_MD5)
    assert "\n" not in str(exc_info.value)

    mock_root_xml = mocker.Mock()
    mock_root_xml.ok = False
    mock_root_xml.status_code = 401
    mock_root_xml.content = (
        b'<?xml version="1.0" encoding="UTF-8"?>\n'
        b"<error>\n  <error-message>'Invalid apikey or expired apikey'</error-message>\n</error>"
    )
    mock_root_xml.text = "raw xml body"
    mocker.patch.object(mgr.session, "request", return_value=mock_root_xml)

    with pytest.raises(
        WildfireManagerError,
        match=(
            f"Unable to get sample of {SAMPLE_MD5}: "
            "Palo Alto Wildfire request failed with status code 401: 'Invalid apikey or expired apikey'"
        ),
    ) as exc_info:
        mgr.get_sample(SAMPLE_MD5)
    assert "\n" not in str(exc_info.value)

    mock_attr_xml = mocker.Mock()
    mock_attr_xml.ok = False
    mock_attr_xml.status_code = 401
    mock_attr_xml.content = b'<error><error-message code="401">\n  Token\n  expired\n</error-message></error>'
    mock_attr_xml.text = "raw attr fallback"
    mocker.patch.object(mgr.session, "request", return_value=mock_attr_xml)

    with pytest.raises(
        WildfireManagerError,
        match=(
            f"Unable to get sample of {SAMPLE_MD5}: "
            "Palo Alto Wildfire request failed with status code 401: Token expired"
        ),
    ) as exc_info:
        mgr.get_sample(SAMPLE_MD5)
    assert "\n" not in str(exc_info.value)

    mock_empty_xml = mocker.Mock()
    mock_empty_xml.ok = False
    mock_empty_xml.status_code = 400
    mock_empty_xml.content = b"<error><error-message/></error>"
    mock_empty_xml.text = "raw fallback"
    mocker.patch.object(mgr.session, "request", return_value=mock_empty_xml)

    with pytest.raises(
        WildfireManagerError,
        match=(
            f"Unable to get sample of {SAMPLE_MD5}: "
            "Palo Alto Wildfire request failed with status code 400: raw fallback"
        ),
    ):
        mgr.get_sample(SAMPLE_MD5)

    mock_plain = mocker.Mock()
    mock_plain.ok = False
    mock_plain.status_code = 502
    mock_plain.content = b"Bad Gateway"
    mock_plain.text = "Bad Gateway"
    mocker.patch.object(mgr.session, "request", return_value=mock_plain)

    with pytest.raises(
        WildfireManagerError,
        match=(
            f"Unable to get sample of {SAMPLE_MD5}: Palo Alto Wildfire request failed with status code 502: Bad Gateway"
        ),
    ):
        mgr.get_sample(SAMPLE_MD5)


def test_make_request_connection_error(mocker):
    mgr = WildfireManager(api_key="my-secret-key")
    mocker.patch.object(mgr.session, "request", side_effect=requests.exceptions.Timeout("timed out"))

    with pytest.raises(
        WildfireManagerError,
        match=rf"Request to {DEFAULT_API_ROOT}/publicapi/get/sample failed: timed out",
    ):
        mgr.get_sample(SAMPLE_MD5)


def test_get_sample_invalid_hash():
    mgr = WildfireManager(api_key="my-secret-key")
    with pytest.raises(WildfireManagerError, match="Invalid hash 'invalid-hash'"):
        mgr.get_sample("invalid-hash")


def test_get_report_xml(mocker):
    mgr = WildfireManager(
        client_id="test-client-id",
        client_secret="test-secret",
        tsg_id="1234567890",
    )
    mocker.patch.object(mgr, "get_token", return_value="mock-token")

    mock_resp = mocker.Mock()
    mock_resp.ok = True
    mock_resp.status_code = 200
    mock_resp.text = MOCK_XML_REPORT
    mock_resp.content = MOCK_XML_REPORT.encode("utf-8")
    mocker.patch.object(mgr.session, "request", return_value=mock_resp)

    report = mgr.get_report(SAMPLE_MD5)
    assert report["file_info"]["malware"] == "yes"
    assert report["file_info"]["type"] == "PE"


def test_get_pdf_report(mocker):
    mgr = WildfireManager(api_key="my-secret-key")

    mock_resp = mocker.Mock()
    mock_resp.ok = True
    mock_resp.status_code = 200
    mock_resp.text = ""
    mock_resp.content = b"%PDF-1.4 mock pdf data"
    mock_resp.headers = {"Content-Disposition": 'attachment; filename="report.pdf"'}
    mocker.patch.object(mgr.session, "request", return_value=mock_resp)

    result = mgr.get_pdf_report(SAMPLE_MD5)
    assert result["filename"] == "report.pdf"
    assert result["content"] == b"%PDF-1.4 mock pdf data"


def test_get_pdf_report_error_message(mocker):
    mgr = WildfireManager(api_key="my-secret-key")

    mock_resp = mocker.Mock()
    mock_resp.ok = False
    mock_resp.status_code = 500
    mock_resp.content = b"<wildfire><error><error-message>Internal Error</error-message></error></wildfire>"
    mock_resp.text = "Internal Error"
    mocker.patch.object(mgr.session, "request", return_value=mock_resp)

    with pytest.raises(WildfireManagerError, match=f"Unable to get PDF report for {SAMPLE_MD5}: ") as exc_info:
        mgr.get_pdf_report(SAMPLE_MD5)

    assert "\n" not in str(exc_info.value)


def test_get_report_not_found_and_error(mocker):
    mgr = WildfireManager(api_key="my-secret-key")

    mock_404 = mocker.Mock()
    mock_404.ok = False
    mock_404.status_code = 404
    mocker.patch.object(mgr.session, "request", return_value=mock_404)

    with pytest.raises(WildfireNotFoundError, match=f"Report is not available for {SAMPLE_MD5}"):
        mgr.get_report(SAMPLE_MD5)

    mock_500 = mocker.Mock()
    mock_500.ok = False
    mock_500.status_code = 500
    mock_500.content = b"Server Error"
    mock_500.text = "Server Error"
    mocker.patch.object(mgr.session, "request", return_value=mock_500)

    with pytest.raises(
        WildfireManagerError,
        match=(
            f"Unable to get report for {SAMPLE_MD5}: "
            "Palo Alto Wildfire request failed with status code 500: Server Error"
        ),
    ) as exc_info:
        mgr.get_report(SAMPLE_MD5)
    assert "\n" not in str(exc_info.value)


def test_get_pdf_report_not_found(mocker):
    mgr = WildfireManager(api_key="my-secret-key")
    mock_404 = mocker.Mock()
    mock_404.ok = False
    mock_404.status_code = 404
    mocker.patch.object(mgr.session, "request", return_value=mock_404)

    with pytest.raises(WildfireNotFoundError, match=f"PDF report is not available for {SAMPLE_MD5}"):
        mgr.get_pdf_report(SAMPLE_MD5)


def test_get_pcap_not_found_and_error(mocker):
    mgr = WildfireManager(api_key="my-secret-key")

    mock_404 = mocker.Mock()
    mock_404.ok = False
    mock_404.status_code = 404
    mocker.patch.object(mgr.session, "request", return_value=mock_404)

    with pytest.raises(WildfireNotFoundError, match=f"PCAP is not available for {SAMPLE_MD5}"):
        mgr.get_pcap(SAMPLE_MD5)

    mock_500 = mocker.Mock()
    mock_500.ok = False
    mock_500.status_code = 500
    mock_500.content = b"Server Error"
    mock_500.text = "Server Error"
    mocker.patch.object(mgr.session, "request", return_value=mock_500)

    with pytest.raises(
        WildfireManagerError,
        match=(
            f"Unable to get PCAP for {SAMPLE_MD5}: Palo Alto Wildfire request failed with status code 500: Server Error"
        ),
    ) as exc_info:
        mgr.get_pcap(SAMPLE_MD5)
    assert "\n" not in str(exc_info.value)


def test_submit_file_errors(mocker, tmp_path):
    mgr = WildfireManager(api_key="my-secret-key")

    missing = tmp_path / "does_not_exist.bin"
    with pytest.raises(WildfireManagerError, match=re.escape(f"File not found: {missing}")):
        mgr.submit_file(str(missing))

    sample = tmp_path / "sample.bin"
    sample.write_bytes(b"data")

    mock_500 = mocker.Mock()
    mock_500.ok = False
    mock_500.status_code = 500
    mock_500.content = b"Upload Failed"
    mock_500.text = "Upload Failed"
    mocker.patch.object(mgr.session, "request", return_value=mock_500)

    expected = f"Unable to submit file {sample}: Palo Alto Wildfire request failed with status code 500: Upload Failed"
    with pytest.raises(WildfireManagerError, match=re.escape(expected)) as exc_info:
        mgr.submit_file(str(sample))
    assert "\n" not in str(exc_info.value)


def test_test_connectivity_scm(mocker):
    mgr = WildfireManager(
        client_id="test-client-id",
        client_secret="test-secret",
        tsg_id="1234567890",
    )
    mocker.patch.object(mgr, "get_token", return_value="mock-token")

    mock_resp = mocker.Mock()
    mock_resp.ok = True
    mock_resp.status_code = 200
    mock_resp.text = "<wildfire></wildfire>"
    mocker.patch.object(mgr.session, "request", return_value=mock_resp)

    assert mgr.test_connectivity() is True
    assert mgr.get_token.called
