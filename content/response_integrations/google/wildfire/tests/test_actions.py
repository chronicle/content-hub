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

import base64
import sys
import pytest
import soar_sdk

if soar_sdk.__path__[0] not in sys.path:
    sys.path.insert(0, soar_sdk.__path__[0])

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyDataModel import EntityTypes

from ..actions import GetFile, GetReport, Ping

SAMPLE_MD5 = "44d88612fea8a8f36de82e1278abb02f"
SAMPLE_SHA256 = "275a021bbfb6489e54d471899f7db9d1663fc695ec2fe2a2c4538aabf651fd0f"


class MockEntity:
    def __init__(self, identifier: str, entity_type: int = EntityTypes.FILEHASH):
        self.identifier = identifier
        self.entity_type = entity_type
        self.additional_properties = {}
        self.is_suspicious = False


@pytest.fixture(autouse=True)
def mock_sys_argv(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["script.py", "test_api_key"])


def test_get_file_action_with_param(mocker):
    mock_siemplify = mocker.Mock()
    mock_siemplify.parameters = {"File Hash": SAMPLE_SHA256}
    mock_siemplify.target_entities = []

    mocker.patch.object(GetFile, "SiemplifyAction", return_value=mock_siemplify)
    mocker.patch.object(GetFile, "extract_action_param", return_value=SAMPLE_SHA256)

    mock_mgr = mocker.Mock()
    mock_mgr.get_sample.return_value = {
        "filename": "sample.tar",
        "content": b"sample_bytes",
    }
    mocker.patch.object(
        GetFile.WildfireManager,
        "from_siemplify",
        return_value=mock_mgr,
    )

    GetFile.main()

    mock_mgr.get_sample.assert_called_once_with(SAMPLE_SHA256)
    expected_b64 = base64.b64encode(b"sample_bytes").decode("utf-8")
    mock_siemplify.result.add_attachment.assert_called_once_with("sample.tar", expected_b64)
    mock_siemplify.end.assert_called_once_with(
        f"Successfully downloaded file sample for {SAMPLE_SHA256} from Wildfire.",
        True,
        EXECUTION_STATE_COMPLETED,
    )


def test_get_file_action_with_entities(mocker):
    entity = MockEntity(SAMPLE_MD5, EntityTypes.FILEHASH)
    mock_siemplify = mocker.Mock()
    mock_siemplify.parameters = {}
    mock_siemplify.target_entities = [entity]

    mocker.patch.object(GetFile, "SiemplifyAction", return_value=mock_siemplify)
    mocker.patch.object(GetFile, "extract_action_param", return_value="")

    mock_mgr = mocker.Mock()
    mock_mgr.get_sample.return_value = {
        "filename": f"{SAMPLE_MD5}.tar",
        "content": b"sample_bytes_entity",
    }
    mocker.patch.object(
        GetFile.WildfireManager,
        "from_siemplify",
        return_value=mock_mgr,
    )

    GetFile.main()

    mock_mgr.get_sample.assert_called_once_with(SAMPLE_MD5)
    expected_b64 = base64.b64encode(b"sample_bytes_entity").decode("utf-8")
    mock_siemplify.result.add_entity_attachment.assert_called_once_with(
        SAMPLE_MD5, f"{SAMPLE_MD5}.tar", expected_b64
    )
    assert mock_siemplify.end.called


def test_get_report_action_with_param(mocker):
    mock_siemplify = mocker.Mock()
    mock_siemplify.parameters = {"File Hash": SAMPLE_MD5}
    mock_siemplify.target_entities = []

    mocker.patch.object(GetReport, "SiemplifyAction", return_value=mock_siemplify)
    mocker.patch.object(GetReport, "extract_action_param", return_value=SAMPLE_MD5)

    mock_mgr = mocker.Mock()
    mock_mgr.get_report.return_value = {
        "file_info": {"malware": "yes", "md5": SAMPLE_MD5}
    }
    mock_mgr.get_pdf_report.return_value = {
        "filename": f"{SAMPLE_MD5}.pdf",
        "content": b"%PDF data",
    }
    mocker.patch.object(
        GetReport.WildfireManager,
        "from_siemplify",
        return_value=mock_mgr,
    )

    GetReport.main()

    mock_mgr.get_report.assert_called_once_with(SAMPLE_MD5)
    mock_siemplify.result.add_result_json.assert_called_once_with(
        {"file_info": {"malware": "yes", "md5": SAMPLE_MD5}}
    )
    mock_siemplify.end.assert_called_once_with(
        f"Successfully downloaded report for {SAMPLE_MD5} from Wildfire.",
        True,
        EXECUTION_STATE_COMPLETED,
    )


def test_ping_action_success(mocker):
    mock_siemplify = mocker.Mock()
    mocker.patch.object(Ping, "SiemplifyAction", return_value=mock_siemplify)

    mock_mgr = mocker.Mock()
    mock_mgr.test_connectivity.return_value = True
    mocker.patch.object(
        Ping.WildfireManager,
        "from_siemplify",
        return_value=mock_mgr,
    )

    Ping.main()

    mock_siemplify.end.assert_called_once_with(
        "Successfully connected to the Wildfire service.", True, EXECUTION_STATE_COMPLETED
    )


def test_ping_action_failure(mocker):
    mock_siemplify = mocker.Mock()
    mocker.patch.object(Ping, "SiemplifyAction", return_value=mock_siemplify)

    mock_mgr = mocker.Mock()
    mock_mgr.test_connectivity.side_effect = RuntimeError("Invalid SCM credentials")
    mocker.patch.object(
        Ping.WildfireManager,
        "from_siemplify",
        return_value=mock_mgr,
    )

    Ping.main()

    mock_siemplify.end.assert_called_once_with(
        "Failed to connect to the Wildfire service. Reason: Invalid SCM credentials",
        False,
        EXECUTION_STATE_FAILED,
    )
