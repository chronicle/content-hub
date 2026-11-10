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

import time
import pytest
import requests

from ..core.WildfireManager import (
    DEFAULT_API_ROOT,
    DEFAULT_TOKEN_URL,
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
    with pytest.raises(WildfireManagerError, match="Either 'Api Key' or"):
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

    with pytest.raises(WildfireManagerError, match=f"Sample is not available for {SAMPLE_MD5}"):
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
