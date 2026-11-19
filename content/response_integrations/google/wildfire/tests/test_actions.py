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
from typing import Any

import soar_sdk

if soar_sdk.__path__[0] not in sys.path:
    sys.path.insert(0, soar_sdk.__path__[0])

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED, ScriptResult
from soar_sdk.SiemplifyDataModel import EntityTypes

from ..actions import DetonateFile, GetFile, GetPcap, GetReport, Ping
from ..core.WildfireManager import WildfireManagerError, WildfireNotFoundError

SAMPLE_MD5 = "44d88612fea8a8f36de82e1278abb02f"
SAMPLE_MD5_OTHER = "098f6bcd4621d373cade4e832627b4f6"
SAMPLE_SHA256 = "275a021bbfb6489e54d471899f7db9d1663fc695ec2fe2a2c4538aabf651fd0f"


class MockEntity:
    def __init__(self, identifier: str, entity_type: int = EntityTypes.FILEHASH) -> None:
        self.identifier = identifier
        self.entity_type = entity_type
        self.additional_properties: dict[str, Any] = {}
        self.is_suspicious = False


def test_get_file_action_with_param(mocker: Any) -> None:
    mock_siemplify = mocker.Mock()
    mock_siemplify.result = mocker.create_autospec(ScriptResult, instance=True)
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
    mock_siemplify.result.add_attachment.assert_called_once_with(
        f"WildFire sample {SAMPLE_SHA256}", "sample.tar", expected_b64
    )
    mock_siemplify.result.add_result_json.assert_called_once_with([
        {
            "file_hash": SAMPLE_SHA256,
            "filename": "sample.tar",
            "downloaded": True,
        }
    ])
    mock_siemplify.end.assert_called_once_with(
        f"Successfully downloaded file sample for {SAMPLE_SHA256} using Palo Alto Wildfire.",
        True,
        EXECUTION_STATE_COMPLETED,
    )


def test_get_file_action_with_param_not_found(mocker: Any) -> None:
    mock_siemplify = mocker.Mock()
    mock_siemplify.result = mocker.create_autospec(ScriptResult, instance=True)
    mock_siemplify.parameters = {"File Hash": SAMPLE_MD5}
    mock_siemplify.target_entities = []

    mocker.patch.object(GetFile, "SiemplifyAction", return_value=mock_siemplify)
    mocker.patch.object(GetFile, "extract_action_param", return_value=SAMPLE_MD5)

    mock_mgr = mocker.Mock()
    mock_mgr.get_sample.side_effect = WildfireNotFoundError(f"Sample is not available for {SAMPLE_MD5}")
    mocker.patch.object(GetFile.WildfireManager, "from_siemplify", return_value=mock_mgr)

    GetFile.main()

    mock_siemplify.end.assert_called_once_with(
        f"No file sample was found for hash {SAMPLE_MD5} in Palo Alto Wildfire.",
        False,
        EXECUTION_STATE_COMPLETED,
    )


def test_get_file_action_with_entities(mocker: Any) -> None:
    entity = MockEntity(SAMPLE_MD5, EntityTypes.FILEHASH)
    mock_siemplify = mocker.Mock()
    mock_siemplify.result = mocker.create_autospec(ScriptResult, instance=True)
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
    mock_siemplify.result.add_entity_attachment.assert_called_once_with(SAMPLE_MD5, f"{SAMPLE_MD5}.tar", expected_b64)
    mock_siemplify.result.add_result_json.assert_called_once_with([
        {
            "file_hash": SAMPLE_MD5,
            "filename": f"{SAMPLE_MD5}.tar",
            "downloaded": True,
        }
    ])
    mock_siemplify.end.assert_called_once_with(
        f"Successfully downloaded files for the following entities using Palo Alto Wildfire: {SAMPLE_MD5}.",
        True,
        EXECUTION_STATE_COMPLETED,
    )


def test_get_file_action_with_entities_partial_not_found(mocker: Any) -> None:
    e_ok = MockEntity(SAMPLE_MD5, EntityTypes.FILEHASH)
    e_missing = MockEntity(SAMPLE_MD5_OTHER, EntityTypes.FILEHASH)
    mock_siemplify = mocker.Mock()
    mock_siemplify.result = mocker.create_autospec(ScriptResult, instance=True)
    mock_siemplify.parameters = {}
    mock_siemplify.target_entities = [e_ok, e_missing]

    mocker.patch.object(GetFile, "SiemplifyAction", return_value=mock_siemplify)
    mocker.patch.object(GetFile, "extract_action_param", return_value="")

    mock_mgr = mocker.Mock()
    mock_mgr.get_sample.side_effect = [
        {"filename": f"{SAMPLE_MD5}.tar", "content": b"sample_bytes"},
        WildfireNotFoundError(f"Sample is not available for {SAMPLE_MD5_OTHER}"),
    ]
    mocker.patch.object(GetFile.WildfireManager, "from_siemplify", return_value=mock_mgr)

    GetFile.main()

    expected_msg = (
        f"Successfully downloaded files for the following entities using Palo Alto Wildfire: {SAMPLE_MD5}.\n"
        f"Action wasn't able to download files for the following entities using Palo Alto Wildfire: {SAMPLE_MD5_OTHER}."
    )
    mock_siemplify.end.assert_called_once_with(expected_msg, True, EXECUTION_STATE_COMPLETED)


def test_get_file_action_with_entities_partial_hard_error(mocker: Any) -> None:
    e_ok = MockEntity(SAMPLE_MD5, EntityTypes.FILEHASH)
    e_err = MockEntity(SAMPLE_MD5_OTHER, EntityTypes.FILEHASH)
    mock_siemplify = mocker.Mock()
    mock_siemplify.result = mocker.create_autospec(ScriptResult, instance=True)
    mock_siemplify.parameters = {}
    mock_siemplify.target_entities = [e_ok, e_err]

    mocker.patch.object(GetFile, "SiemplifyAction", return_value=mock_siemplify)
    mocker.patch.object(GetFile, "extract_action_param", return_value="")

    mock_mgr = mocker.Mock()
    mock_mgr.get_sample.side_effect = [
        {"filename": f"{SAMPLE_MD5}.tar", "content": b"sample_bytes"},
        WildfireManagerError("Rate limit exceeded"),
    ]
    mocker.patch.object(GetFile.WildfireManager, "from_siemplify", return_value=mock_mgr)

    GetFile.main()

    expected_msg = (
        f"Successfully downloaded files for the following entities using Palo Alto Wildfire: {SAMPLE_MD5}.\n"
        f"Action wasn't able to download files for the following entities using "
        f"Palo Alto Wildfire: {SAMPLE_MD5_OTHER}.\n"
        f"Errors:\n{SAMPLE_MD5_OTHER}: Rate limit exceeded"
    )
    mock_siemplify.end.assert_called_once_with(expected_msg, True, EXECUTION_STATE_COMPLETED)


def test_get_file_action_with_entities_all_not_found(mocker: Any) -> None:
    entity = MockEntity(SAMPLE_MD5, EntityTypes.FILEHASH)
    mock_siemplify = mocker.Mock()
    mock_siemplify.result = mocker.create_autospec(ScriptResult, instance=True)
    mock_siemplify.parameters = {}
    mock_siemplify.target_entities = [entity]

    mocker.patch.object(GetFile, "SiemplifyAction", return_value=mock_siemplify)
    mocker.patch.object(GetFile, "extract_action_param", return_value="")

    mock_mgr = mocker.Mock()
    mock_mgr.get_sample.side_effect = WildfireNotFoundError(f"Sample is not available for {SAMPLE_MD5}")
    mocker.patch.object(GetFile.WildfireManager, "from_siemplify", return_value=mock_mgr)

    GetFile.main()

    expected_msg = (
        "No files were downloaded using Palo Alto Wildfire.\n"
        f"Action wasn't able to download files for the following entities using Palo Alto Wildfire: {SAMPLE_MD5}."
    )
    mock_siemplify.end.assert_called_once_with(expected_msg, False, EXECUTION_STATE_COMPLETED)


def test_get_file_action_with_entities_empty(mocker: Any) -> None:
    mock_siemplify = mocker.Mock()
    mock_siemplify.result = mocker.create_autospec(ScriptResult, instance=True)
    mock_siemplify.parameters = {}
    mock_siemplify.target_entities = []

    mocker.patch.object(GetFile, "SiemplifyAction", return_value=mock_siemplify)
    mocker.patch.object(GetFile, "extract_action_param", return_value="")
    mocker.patch.object(GetFile.WildfireManager, "from_siemplify", return_value=mocker.Mock())

    GetFile.main()

    mock_siemplify.end.assert_called_once_with(
        "No files were downloaded using Palo Alto Wildfire.",
        False,
        EXECUTION_STATE_COMPLETED,
    )


def test_get_file_action_with_entities_all_hard_error(mocker: Any) -> None:
    entity = MockEntity(SAMPLE_MD5, EntityTypes.FILEHASH)
    mock_siemplify = mocker.Mock()
    mock_siemplify.result = mocker.create_autospec(ScriptResult, instance=True)
    mock_siemplify.parameters = {}
    mock_siemplify.target_entities = [entity]

    mocker.patch.object(GetFile, "SiemplifyAction", return_value=mock_siemplify)
    mocker.patch.object(GetFile, "extract_action_param", return_value="")

    mock_mgr = mocker.Mock()
    mock_mgr.get_sample.side_effect = WildfireManagerError("Unauthorized")
    mocker.patch.object(GetFile.WildfireManager, "from_siemplify", return_value=mock_mgr)

    GetFile.main()

    mock_siemplify.end.assert_called_once_with(
        f'Error executing action "Get File". Reason: {SAMPLE_MD5}: Unauthorized',
        False,
        EXECUTION_STATE_FAILED,
    )


def test_get_file_action_failure(mocker: Any) -> None:
    mock_siemplify = mocker.Mock()
    mock_siemplify.result = mocker.create_autospec(ScriptResult, instance=True)
    mock_siemplify.parameters = {"File Hash": SAMPLE_MD5}
    mock_siemplify.target_entities = []

    mocker.patch.object(GetFile, "SiemplifyAction", return_value=mock_siemplify)
    mocker.patch.object(GetFile, "extract_action_param", return_value=SAMPLE_MD5)

    mock_mgr = mocker.Mock()
    mock_mgr.get_sample.side_effect = RuntimeError("HTTP 500 Internal Server Error")
    mocker.patch.object(GetFile.WildfireManager, "from_siemplify", return_value=mock_mgr)

    GetFile.main()

    mock_siemplify.end.assert_called_once_with(
        'Error executing action "Get File". Reason: HTTP 500 Internal Server Error',
        False,
        EXECUTION_STATE_FAILED,
    )


def test_get_file_action_init_failure(mocker: Any) -> None:
    mock_siemplify = mocker.Mock()
    mocker.patch.object(GetFile, "SiemplifyAction", return_value=mock_siemplify)
    mocker.patch.object(GetFile, "extract_action_param", return_value="")
    mocker.patch.object(GetFile.WildfireManager, "from_siemplify", side_effect=Exception("Missing config"))

    GetFile.main()

    mock_siemplify.end.assert_called_once_with(
        'Error executing action "Get File". Reason: Missing config',
        False,
        EXECUTION_STATE_FAILED,
    )


def test_get_report_action_with_param(mocker: Any) -> None:
    mock_siemplify = mocker.Mock()
    mock_siemplify.result = mocker.create_autospec(ScriptResult, instance=True)
    mock_siemplify.parameters = {"File Hash": SAMPLE_MD5}
    mock_siemplify.target_entities = []

    mocker.patch.object(GetReport, "SiemplifyAction", return_value=mock_siemplify)
    mocker.patch.object(GetReport, "extract_action_param", return_value=SAMPLE_MD5)

    report_data = {
        "file_info": {"malware": "yes", "md5": SAMPLE_MD5},
        "task_info": {"report": {"verdict": "malware"}},
    }
    mock_mgr = mocker.Mock()
    mock_mgr.get_report.return_value = report_data
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
    mock_mgr.get_pdf_report.assert_called_once_with(SAMPLE_MD5)
    mock_siemplify.result.add_result_json.assert_called_once_with([report_data])
    mock_siemplify.result.add_attachment.assert_called_once()
    mock_siemplify.result.add_data_table.assert_called_once()
    mock_siemplify.end.assert_called_once_with(
        f"Successfully downloaded report for {SAMPLE_MD5} using Palo Alto Wildfire.",
        True,
        EXECUTION_STATE_COMPLETED,
    )


def test_get_report_action_with_param_not_found(mocker: Any) -> None:
    mock_siemplify = mocker.Mock()
    mock_siemplify.result = mocker.create_autospec(ScriptResult, instance=True)
    mock_siemplify.parameters = {"File Hash": SAMPLE_MD5}
    mock_siemplify.target_entities = []

    mocker.patch.object(GetReport, "SiemplifyAction", return_value=mock_siemplify)
    mocker.patch.object(GetReport, "extract_action_param", return_value=SAMPLE_MD5)

    mock_mgr = mocker.Mock()
    mock_mgr.get_report.side_effect = WildfireNotFoundError(f"Report is not available for {SAMPLE_MD5}")
    mocker.patch.object(GetReport.WildfireManager, "from_siemplify", return_value=mock_mgr)

    GetReport.main()

    mock_siemplify.end.assert_called_once_with(
        f"No report was found for hash {SAMPLE_MD5} in Palo Alto Wildfire.",
        False,
        EXECUTION_STATE_COMPLETED,
    )


def test_get_report_action_with_entities(mocker: Any) -> None:
    entity = MockEntity(SAMPLE_MD5, EntityTypes.FILEHASH)
    mock_siemplify = mocker.Mock()
    mock_siemplify.result = mocker.create_autospec(ScriptResult, instance=True)
    mock_siemplify.parameters = {}
    mock_siemplify.target_entities = [entity]

    mocker.patch.object(GetReport, "SiemplifyAction", return_value=mock_siemplify)
    mocker.patch.object(GetReport, "extract_action_param", return_value="")

    report_data = {
        "file_info": {"malware": "yes", "md5": SAMPLE_MD5},
        "task_info": {"report": {"verdict": "malware"}},
    }
    mock_mgr = mocker.Mock()
    mock_mgr.get_report.return_value = report_data
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
    mock_mgr.get_pdf_report.assert_called_once_with(SAMPLE_MD5)
    mock_siemplify.result.add_result_json.assert_called_once_with([report_data])
    mock_siemplify.result.add_entity_attachment.assert_called_once()
    mock_siemplify.result.add_entity_table.assert_called_once()
    mock_siemplify.end.assert_called_once_with(
        f"Successfully enriched the following entities using Palo Alto Wildfire: {SAMPLE_MD5}.",
        True,
        EXECUTION_STATE_COMPLETED,
    )


def test_get_report_action_with_entities_partial_not_found(mocker: Any) -> None:
    e_ok = MockEntity(SAMPLE_MD5, EntityTypes.FILEHASH)
    e_missing = MockEntity(SAMPLE_MD5_OTHER, EntityTypes.FILEHASH)
    mock_siemplify = mocker.Mock()
    mock_siemplify.result = mocker.create_autospec(ScriptResult, instance=True)
    mock_siemplify.parameters = {}
    mock_siemplify.target_entities = [e_ok, e_missing]

    mocker.patch.object(GetReport, "SiemplifyAction", return_value=mock_siemplify)
    mocker.patch.object(GetReport, "extract_action_param", return_value="")

    report_data = {
        "file_info": {"malware": "no", "md5": SAMPLE_MD5},
        "task_info": {"report": {"verdict": "benign"}},
    }
    mock_mgr = mocker.Mock()
    mock_mgr.get_report.side_effect = [
        report_data,
        WildfireNotFoundError(f"Report is not available for {SAMPLE_MD5_OTHER}"),
    ]
    mock_mgr.get_pdf_report.return_value = {"filename": f"{SAMPLE_MD5}.pdf", "content": b"%PDF"}
    mocker.patch.object(GetReport.WildfireManager, "from_siemplify", return_value=mock_mgr)

    GetReport.main()

    expected_msg = (
        f"Successfully enriched the following entities using Palo Alto Wildfire: {SAMPLE_MD5}.\n"
        f"Action wasn't able to enrich the following entities using Palo Alto Wildfire: {SAMPLE_MD5_OTHER}."
    )
    mock_siemplify.end.assert_called_once_with(expected_msg, True, EXECUTION_STATE_COMPLETED)


def test_get_report_action_with_entities_partial_hard_error(mocker: Any) -> None:
    e_ok = MockEntity(SAMPLE_MD5, EntityTypes.FILEHASH)
    e_err = MockEntity(SAMPLE_MD5_OTHER, EntityTypes.FILEHASH)
    mock_siemplify = mocker.Mock()
    mock_siemplify.result = mocker.create_autospec(ScriptResult, instance=True)
    mock_siemplify.parameters = {}
    mock_siemplify.target_entities = [e_ok, e_err]

    mocker.patch.object(GetReport, "SiemplifyAction", return_value=mock_siemplify)
    mocker.patch.object(GetReport, "extract_action_param", return_value="")

    report_data = {
        "file_info": {"malware": "no", "md5": SAMPLE_MD5},
        "task_info": {"report": {"verdict": "benign"}},
    }
    mock_mgr = mocker.Mock()
    mock_mgr.get_report.side_effect = [
        report_data,
        WildfireManagerError("Rate limit exceeded"),
    ]
    mock_mgr.get_pdf_report.return_value = {"filename": f"{SAMPLE_MD5}.pdf", "content": b"%PDF"}
    mocker.patch.object(GetReport.WildfireManager, "from_siemplify", return_value=mock_mgr)

    GetReport.main()

    expected_msg = (
        f"Successfully enriched the following entities using Palo Alto Wildfire: {SAMPLE_MD5}.\n"
        f"Action wasn't able to enrich the following entities using Palo Alto Wildfire: {SAMPLE_MD5_OTHER}.\n"
        f"Errors:\n{SAMPLE_MD5_OTHER}: Rate limit exceeded"
    )
    mock_siemplify.end.assert_called_once_with(expected_msg, True, EXECUTION_STATE_COMPLETED)


def test_get_report_action_with_entities_empty(mocker: Any) -> None:
    mock_siemplify = mocker.Mock()
    mock_siemplify.result = mocker.create_autospec(ScriptResult, instance=True)
    mock_siemplify.parameters = {}
    mock_siemplify.target_entities = []

    mocker.patch.object(GetReport, "SiemplifyAction", return_value=mock_siemplify)
    mocker.patch.object(GetReport, "extract_action_param", return_value="")
    mocker.patch.object(GetReport.WildfireManager, "from_siemplify", return_value=mocker.Mock())

    GetReport.main()

    mock_siemplify.end.assert_called_once_with(
        "None of the provided entities were enriched.",
        False,
        EXECUTION_STATE_COMPLETED,
    )


def test_get_report_action_with_entities_all_not_found(mocker: Any) -> None:
    entity = MockEntity(SAMPLE_MD5, EntityTypes.FILEHASH)
    mock_siemplify = mocker.Mock()
    mock_siemplify.result = mocker.create_autospec(ScriptResult, instance=True)
    mock_siemplify.parameters = {}
    mock_siemplify.target_entities = [entity]

    mocker.patch.object(GetReport, "SiemplifyAction", return_value=mock_siemplify)
    mocker.patch.object(GetReport, "extract_action_param", return_value="")

    mock_mgr = mocker.Mock()
    mock_mgr.get_report.side_effect = WildfireNotFoundError(f"Report is not available for {SAMPLE_MD5}")
    mocker.patch.object(GetReport.WildfireManager, "from_siemplify", return_value=mock_mgr)

    GetReport.main()

    expected_msg = (
        "None of the provided entities were enriched.\n"
        f"Action wasn't able to enrich the following entities using Palo Alto Wildfire: {SAMPLE_MD5}."
    )
    mock_siemplify.end.assert_called_once_with(expected_msg, False, EXECUTION_STATE_COMPLETED)


def test_get_report_action_with_entities_all_hard_error(mocker: Any) -> None:
    entity = MockEntity(SAMPLE_MD5, EntityTypes.FILEHASH)
    mock_siemplify = mocker.Mock()
    mock_siemplify.result = mocker.create_autospec(ScriptResult, instance=True)
    mock_siemplify.parameters = {}
    mock_siemplify.target_entities = [entity]

    mocker.patch.object(GetReport, "SiemplifyAction", return_value=mock_siemplify)
    mocker.patch.object(GetReport, "extract_action_param", return_value="")

    mock_mgr = mocker.Mock()
    mock_mgr.get_report.side_effect = WildfireManagerError("Unauthorized")
    mocker.patch.object(GetReport.WildfireManager, "from_siemplify", return_value=mock_mgr)

    GetReport.main()

    mock_siemplify.end.assert_called_once_with(
        f'Error executing action "Get Report". Reason: {SAMPLE_MD5}: Unauthorized',
        False,
        EXECUTION_STATE_FAILED,
    )


def test_get_report_action_failure(mocker: Any) -> None:
    mock_siemplify = mocker.Mock()
    mock_siemplify.result = mocker.create_autospec(ScriptResult, instance=True)
    mock_siemplify.parameters = {"File Hash": SAMPLE_MD5}
    mock_siemplify.target_entities = []

    mocker.patch.object(GetReport, "SiemplifyAction", return_value=mock_siemplify)
    mocker.patch.object(GetReport, "extract_action_param", return_value=SAMPLE_MD5)

    mock_mgr = mocker.Mock()
    mock_mgr.get_report.side_effect = RuntimeError("WildFire report unavailable")
    mocker.patch.object(GetReport.WildfireManager, "from_siemplify", return_value=mock_mgr)

    GetReport.main()

    mock_siemplify.end.assert_called_once_with(
        'Error executing action "Get Report". Reason: WildFire report unavailable',
        False,
        EXECUTION_STATE_FAILED,
    )


def test_get_report_action_init_failure(mocker: Any) -> None:
    mock_siemplify = mocker.Mock()
    mocker.patch.object(GetReport, "SiemplifyAction", return_value=mock_siemplify)
    mocker.patch.object(GetReport, "extract_action_param", return_value="")
    mocker.patch.object(GetReport.WildfireManager, "from_siemplify", side_effect=Exception("Missing config"))

    GetReport.main()

    mock_siemplify.end.assert_called_once_with(
        'Error executing action "Get Report". Reason: Missing config',
        False,
        EXECUTION_STATE_FAILED,
    )


def test_detonate_file_action(mocker: Any) -> None:
    mocker.patch.object(DetonateFile, "time", mocker.Mock(sleep=mocker.Mock()))
    mock_siemplify = mocker.Mock()
    mock_siemplify.result = mocker.create_autospec(ScriptResult, instance=True)
    mock_siemplify.parameters = {"File Paths": "test.exe"}
    mock_siemplify.case_id = "12345"

    mocker.patch.object(DetonateFile, "SiemplifyAction", return_value=mock_siemplify)
    mocker.patch.object(DetonateFile, "extract_action_param", return_value="test.exe")

    mock_mgr = mocker.Mock()
    mock_mgr.submit_file.return_value = {"md5": SAMPLE_MD5}
    mock_mgr.get_report.return_value = {
        "file_info": {"malware": "no", "md5": SAMPLE_MD5},
        "task_info": {"report": {"verdict": "benign"}},
    }
    mock_mgr.get_pdf_report.return_value = {
        "filename": "test.pdf",
        "content": b"%PDF data",
    }
    mocker.patch.object(DetonateFile.WildfireManager, "from_siemplify", return_value=mock_mgr)

    DetonateFile.main()

    mock_mgr.submit_file.assert_called_once_with("test.exe")
    mock_siemplify.result.add_attachment.assert_called_once()
    mock_siemplify.end.assert_called_once_with(
        "Successfully uploaded files and downloaded reports using Palo Alto Wildfire: test.exe.",
        True,
        EXECUTION_STATE_COMPLETED,
    )


def test_detonate_file_action_init_failure(mocker: Any) -> None:
    mock_siemplify = mocker.Mock()
    mock_siemplify.parameters = {"File Paths": "test.exe"}
    mocker.patch.object(DetonateFile, "SiemplifyAction", return_value=mock_siemplify)
    mocker.patch.object(DetonateFile, "extract_action_param", return_value="test.exe")
    mocker.patch.object(DetonateFile.WildfireManager, "from_siemplify", side_effect=Exception("Missing config"))

    DetonateFile.main()

    mock_siemplify.end.assert_called_once_with(
        'Error executing action "Detonate File". Reason: Missing config', False, EXECUTION_STATE_FAILED
    )


def test_detonate_file_action_submit_failure(mocker: Any) -> None:
    mock_siemplify = mocker.Mock()
    mock_siemplify.parameters = {"File Paths": "missing.exe"}
    mocker.patch.object(DetonateFile, "SiemplifyAction", return_value=mock_siemplify)
    mocker.patch.object(DetonateFile, "extract_action_param", return_value="missing.exe")

    mock_mgr = mocker.Mock()
    mock_mgr.submit_file.side_effect = WildfireManagerError("File not found: missing.exe")
    mocker.patch.object(DetonateFile.WildfireManager, "from_siemplify", return_value=mock_mgr)

    DetonateFile.main()

    mock_siemplify.end.assert_called_once_with(
        'Error executing action "Detonate File". Reason: File not found: missing.exe',
        False,
        EXECUTION_STATE_FAILED,
    )


def test_detonate_file_action_empty_paths(mocker: Any) -> None:
    mock_siemplify = mocker.Mock()
    mocker.patch.object(DetonateFile, "SiemplifyAction", return_value=mock_siemplify)
    mocker.patch.object(DetonateFile, "extract_action_param", return_value=" , ")

    DetonateFile.main()

    mock_siemplify.end.assert_called_once_with(
        'Error executing action "Detonate File". Reason: At least one file path must be provided.',
        False,
        EXECUTION_STATE_FAILED,
    )


def test_detonate_file_action_pdf_failure(mocker: Any) -> None:
    mocker.patch.object(DetonateFile, "time", mocker.Mock(sleep=mocker.Mock()))
    mock_siemplify = mocker.Mock()
    mock_siemplify.result = mocker.create_autospec(ScriptResult, instance=True)
    mock_siemplify.parameters = {"File Paths": "test.exe"}
    mock_siemplify.case_id = "12345"

    mocker.patch.object(DetonateFile, "SiemplifyAction", return_value=mock_siemplify)
    mocker.patch.object(DetonateFile, "extract_action_param", return_value="test.exe")

    mock_mgr = mocker.Mock()
    mock_mgr.submit_file.return_value = {"md5": SAMPLE_MD5}
    mock_mgr.get_report.return_value = {
        "file_info": {"malware": "no", "md5": SAMPLE_MD5},
        "task_info": {"report": {"verdict": "benign"}},
    }
    mock_mgr.get_pdf_report.side_effect = WildfireManagerError(f"Unable to get PDF report for {SAMPLE_MD5}: HTTP 500")
    mocker.patch.object(DetonateFile.WildfireManager, "from_siemplify", return_value=mock_mgr)

    DetonateFile.main()

    mock_siemplify.end.assert_called_once_with(
        f'Error executing action "Detonate File". Reason: Unable to get PDF report for {SAMPLE_MD5}: HTTP 500',
        False,
        EXECUTION_STATE_FAILED,
    )


def test_get_pcap_action(mocker: Any) -> None:
    entity = MockEntity(SAMPLE_MD5, EntityTypes.FILEHASH)
    mock_siemplify = mocker.Mock()
    mock_siemplify.result = mocker.create_autospec(ScriptResult, instance=True)
    mock_siemplify.target_entities = [entity]

    mocker.patch.object(GetPcap, "SiemplifyAction", return_value=mock_siemplify)

    mock_mgr = mocker.Mock()
    mock_mgr.get_pcap.return_value = {
        "filename": f"{SAMPLE_MD5}.pcap",
        "content": b"PCAPDATA",
    }
    mocker.patch.object(GetPcap.WildfireManager, "from_siemplify", return_value=mock_mgr)

    GetPcap.main()

    mock_mgr.get_pcap.assert_called_once_with(SAMPLE_MD5)
    mock_siemplify.result.add_entity_attachment.assert_called_once()
    mock_siemplify.end.assert_called_once_with(
        f"Successfully downloaded PCAP files for the following entities using Palo Alto Wildfire: {SAMPLE_MD5}.",
        True,
        EXECUTION_STATE_COMPLETED,
    )


def test_get_pcap_action_partial_not_found(mocker: Any) -> None:
    e_ok = MockEntity(SAMPLE_MD5, EntityTypes.FILEHASH)
    e_missing = MockEntity(SAMPLE_MD5_OTHER, EntityTypes.FILEHASH)
    mock_siemplify = mocker.Mock()
    mock_siemplify.result = mocker.create_autospec(ScriptResult, instance=True)
    mock_siemplify.target_entities = [e_ok, e_missing]

    mocker.patch.object(GetPcap, "SiemplifyAction", return_value=mock_siemplify)

    mock_mgr = mocker.Mock()
    mock_mgr.get_pcap.side_effect = [
        {"filename": f"{SAMPLE_MD5}.pcap", "content": b"PCAPDATA"},
        WildfireNotFoundError(f"PCAP is not available for {SAMPLE_MD5_OTHER}"),
    ]
    mocker.patch.object(GetPcap.WildfireManager, "from_siemplify", return_value=mock_mgr)

    GetPcap.main()

    expected_msg = (
        f"Successfully downloaded PCAP files for the following entities using Palo Alto Wildfire: {SAMPLE_MD5}.\n"
        f"Action wasn't able to download PCAP files for the following entities using "
        f"Palo Alto Wildfire: {SAMPLE_MD5_OTHER}."
    )
    mock_siemplify.end.assert_called_once_with(expected_msg, True, EXECUTION_STATE_COMPLETED)


def test_get_pcap_action_partial_hard_error(mocker: Any) -> None:
    e_ok = MockEntity(SAMPLE_MD5, EntityTypes.FILEHASH)
    e_err = MockEntity(SAMPLE_MD5_OTHER, EntityTypes.FILEHASH)
    mock_siemplify = mocker.Mock()
    mock_siemplify.result = mocker.create_autospec(ScriptResult, instance=True)
    mock_siemplify.target_entities = [e_ok, e_err]

    mocker.patch.object(GetPcap, "SiemplifyAction", return_value=mock_siemplify)

    mock_mgr = mocker.Mock()
    mock_mgr.get_pcap.side_effect = [
        {"filename": f"{SAMPLE_MD5}.pcap", "content": b"PCAPDATA"},
        WildfireManagerError("Rate limit exceeded"),
    ]
    mocker.patch.object(GetPcap.WildfireManager, "from_siemplify", return_value=mock_mgr)

    GetPcap.main()

    expected_msg = (
        f"Successfully downloaded PCAP files for the following entities using Palo Alto Wildfire: {SAMPLE_MD5}.\n"
        f"Action wasn't able to download PCAP files for the following entities using "
        f"Palo Alto Wildfire: {SAMPLE_MD5_OTHER}.\n"
        f"Errors:\n{SAMPLE_MD5_OTHER}: Rate limit exceeded"
    )
    mock_siemplify.end.assert_called_once_with(expected_msg, True, EXECUTION_STATE_COMPLETED)


def test_get_pcap_action_empty(mocker: Any) -> None:
    mock_siemplify = mocker.Mock()
    mock_siemplify.result = mocker.create_autospec(ScriptResult, instance=True)
    mock_siemplify.target_entities = []

    mocker.patch.object(GetPcap, "SiemplifyAction", return_value=mock_siemplify)
    mocker.patch.object(GetPcap.WildfireManager, "from_siemplify", return_value=mocker.Mock())

    GetPcap.main()

    mock_siemplify.end.assert_called_once_with(
        "No PCAP files were downloaded using Palo Alto Wildfire.",
        False,
        EXECUTION_STATE_COMPLETED,
    )


def test_get_pcap_action_all_not_found(mocker: Any) -> None:
    entity = MockEntity(SAMPLE_MD5, EntityTypes.FILEHASH)
    mock_siemplify = mocker.Mock()
    mock_siemplify.result = mocker.create_autospec(ScriptResult, instance=True)
    mock_siemplify.target_entities = [entity]

    mocker.patch.object(GetPcap, "SiemplifyAction", return_value=mock_siemplify)

    mock_mgr = mocker.Mock()
    mock_mgr.get_pcap.side_effect = WildfireNotFoundError(f"PCAP is not available for {SAMPLE_MD5}")
    mocker.patch.object(GetPcap.WildfireManager, "from_siemplify", return_value=mock_mgr)

    GetPcap.main()

    expected_msg = (
        "No PCAP files were downloaded using Palo Alto Wildfire.\n"
        f"Action wasn't able to download PCAP files for the following entities using Palo Alto Wildfire: {SAMPLE_MD5}."
    )
    mock_siemplify.end.assert_called_once_with(expected_msg, False, EXECUTION_STATE_COMPLETED)


def test_get_pcap_action_all_hard_error(mocker: Any) -> None:
    entity = MockEntity(SAMPLE_MD5, EntityTypes.FILEHASH)
    mock_siemplify = mocker.Mock()
    mock_siemplify.result = mocker.create_autospec(ScriptResult, instance=True)
    mock_siemplify.target_entities = [entity]

    mocker.patch.object(GetPcap, "SiemplifyAction", return_value=mock_siemplify)

    mock_mgr = mocker.Mock()
    mock_mgr.get_pcap.side_effect = WildfireManagerError("Unauthorized")
    mocker.patch.object(GetPcap.WildfireManager, "from_siemplify", return_value=mock_mgr)

    GetPcap.main()

    mock_siemplify.end.assert_called_once_with(
        f'Error executing action "Get Pcap". Reason: {SAMPLE_MD5}: Unauthorized',
        False,
        EXECUTION_STATE_FAILED,
    )


def test_get_pcap_action_init_failure(mocker: Any) -> None:
    mock_siemplify = mocker.Mock()
    mocker.patch.object(GetPcap, "SiemplifyAction", return_value=mock_siemplify)
    mocker.patch.object(GetPcap.WildfireManager, "from_siemplify", side_effect=Exception("Missing config"))

    GetPcap.main()

    mock_siemplify.end.assert_called_once_with(
        'Error executing action "Get Pcap". Reason: Missing config', False, EXECUTION_STATE_FAILED
    )


def test_ping_action_success(mocker: Any) -> None:
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
        "Successfully connected to the Palo Alto Wildfire server with the provided connection parameters!",
        True,
        EXECUTION_STATE_COMPLETED,
    )


def test_ping_action_failure(mocker: Any) -> None:
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
        'Error executing action "Ping". Reason: '
        "Failed to connect to the Palo Alto Wildfire server: Invalid SCM credentials",
        False,
        EXECUTION_STATE_FAILED,
    )


def test_ping_action_init_failure(mocker: Any) -> None:
    mock_siemplify = mocker.Mock()
    mocker.patch.object(Ping, "SiemplifyAction", return_value=mock_siemplify)
    mocker.patch.object(Ping.WildfireManager, "from_siemplify", side_effect=WildfireManagerError("Missing config"))

    Ping.main()

    mock_siemplify.end.assert_called_once_with(
        'Error executing action "Ping". Reason: Failed to connect to the Palo Alto Wildfire server: Missing config',
        False,
        EXECUTION_STATE_FAILED,
    )
