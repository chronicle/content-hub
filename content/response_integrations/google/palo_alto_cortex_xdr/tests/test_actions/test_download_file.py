from __future__ import annotations

import copy
import datetime
import json
import os
import shutil

from TIPCommon.base.action import ExecutionState, EntityTypesEnum
from TIPCommon.consts import NUM_OF_MILLI_IN_SEC
from TIPCommon.types import Entity, SingleJson

from ...actions import DownloadFile
from ...tests import common
from ...tests.core.product import PaloAltoCortexXDR
from ...tests.core.session import PaloAltoCortexXDRSession
from integration_testing.common import create_entity
from integration_testing.platform.script_output import MockActionOutput
from integration_testing.request import MockRequest
from integration_testing.set_meta import set_metadata


SCRIPT_DEADLINE_TIME: datetime.datetime = datetime.datetime.now() + datetime.timedelta(
    minutes=10
)

SUCCESS_OUTPUT_MESSAGE: str = "Successfully downloaded files from the following endpoints in Palo Alto XDR"
KEY_CALC: str = "ep1:C:\\Windows\\System32\\calc.exe"
KEY_PASSWD: str = "ep1:/etc/passwd"

IP_ENTITY: Entity = create_entity(
    identifier=common.ENDPOINT_IP.ip[0],
    type_=EntityTypesEnum.ADDRESS,
)

TEST_DOWNLOAD_DIR_FIRST_RUN: str = "/tmp/cortex_retrievals_first_run"
TEST_DOWNLOAD_DIR_IP_PARAM: str = "/tmp/cortex_retrievals_ip_param"
TEST_DOWNLOAD_DIR_POLLING: str = "/tmp/cortex_retrievals_polling"

DEFAULT_PARAMS: SingleJson = {
    "Incident ID": "12345",
    "File Paths": "C:\\Windows\\System32\\calc.exe, /etc/passwd",
    "Agent ID": "ep1",
    "Download Folder Path": TEST_DOWNLOAD_DIR_FIRST_RUN,
    "Overwrite": "False",
}

DEFAULT_PARAMS_WITH_IP: SingleJson = {
    "Incident ID": "12345",
    "File Paths": "C:\\Windows\\System32\\calc.exe, /etc/passwd",
    "Agent ID": "192.168.1.100",
    "Download Folder Path": TEST_DOWNLOAD_DIR_IP_PARAM,
    "Overwrite": "False",
}

POLLING_PARAMS: SingleJson = {
    "Incident ID": "12345",
    "File Paths": "C:\\Windows\\System32\\calc.exe, /etc/passwd",
    "Agent ID": "",
    "Download Folder Path": TEST_DOWNLOAD_DIR_POLLING,
    "Overwrite": "False",
    "additional_data": json.dumps(common.STATE_IN_PROGRESS),
}


def teardown_module():
    """Clean up temporary download directories after running the test module."""
    for folder in [
        TEST_DOWNLOAD_DIR_FIRST_RUN,
        TEST_DOWNLOAD_DIR_IP_PARAM,
        TEST_DOWNLOAD_DIR_POLLING,
    ]:
        if os.path.exists(folder):
            shutil.rmtree(folder)


@set_metadata(
    integration_config=common.CONFIG,
    parameters=DEFAULT_PARAMS,
    entities=[IP_ENTITY],
)
def test_download_file_first_run_success(
    palo_alto_cortex_xdr: PaloAltoCortexXDR,
    script_session: PaloAltoCortexXDRSession,
    action_output: MockActionOutput,
) -> None:
    """Test successful initiation of file retrieval on first run."""
    endpoint_data: SingleJson = copy.deepcopy(common.ENDPOINT_IP.raw_data)
    endpoint_data["endpoint_id"] = "ep1"
    endpoint_data["os_type"] = "windows"
    palo_alto_cortex_xdr.add_endpoint(endpoint_data)
    palo_alto_cortex_xdr.add_file_retrieval_action(common.RETRIEVAL_ACTION)

    if os.path.exists(TEST_DOWNLOAD_DIR_FIRST_RUN):
        shutil.rmtree(TEST_DOWNLOAD_DIR_FIRST_RUN)
    os.makedirs(TEST_DOWNLOAD_DIR_FIRST_RUN)

    DownloadFile.main()

    assert len(script_session.request_history) >= 2
    assert action_output.results.execution_state == ExecutionState.IN_PROGRESS

    file_retrieval_request: MockRequest = next(
        req.request
        for req in script_session.request_history
        if "endpoints/file_retrieval/" in req.request.url.path
    )
    request_data: SingleJson = file_retrieval_request.kwargs.get("json", {}).get(
        "request_data", {}
    )
    assert request_data.get("incident_id") == 12345

    state: SingleJson = json.loads(action_output.results.result_value)
    endpoints_data: SingleJson = state.get("endpoints_data", {})

    assert KEY_CALC in endpoints_data
    assert KEY_PASSWD in endpoints_data

    assert endpoints_data[KEY_CALC]["status"] == "Pending"
    assert endpoints_data[KEY_CALC]["group_id"] == str(
        common.RETRIEVAL_ACTION.action_id
    )
    assert (
        endpoints_data[KEY_CALC]["identifier"]
        == common.MOCK_DATA["endpoint_data_ip"]["ip"][0]
    )


@set_metadata(
    integration_config=common.CONFIG,
    parameters=DEFAULT_PARAMS_WITH_IP,
    entities=[],
)
def test_download_file_by_ip_param_first_run_success(
    palo_alto_cortex_xdr: PaloAltoCortexXDR,
    action_output: MockActionOutput,
) -> None:
    """
    Test successful initiation of file retrieval when IP is passed in Agent ID field.
    """
    endpoint_data: SingleJson = copy.deepcopy(common.ENDPOINT_IP.raw_data)
    endpoint_data["endpoint_id"] = "ep1"
    endpoint_data["os_type"] = "windows"
    palo_alto_cortex_xdr.add_endpoint(endpoint_data)
    palo_alto_cortex_xdr.add_file_retrieval_action(common.RETRIEVAL_ACTION)

    if os.path.exists(TEST_DOWNLOAD_DIR_IP_PARAM):
        shutil.rmtree(TEST_DOWNLOAD_DIR_IP_PARAM)
    os.makedirs(TEST_DOWNLOAD_DIR_IP_PARAM)

    DownloadFile.main()

    assert action_output.results.execution_state == ExecutionState.IN_PROGRESS

    state: SingleJson = json.loads(action_output.results.result_value)
    endpoints_data: SingleJson = state.get("endpoints_data", {})

    assert KEY_CALC in endpoints_data
    assert KEY_PASSWD in endpoints_data

    assert endpoints_data[KEY_CALC]["status"] == "Pending"
    assert endpoints_data[KEY_CALC]["group_id"] == str(
        common.RETRIEVAL_ACTION.action_id
    )
    assert endpoints_data[KEY_CALC]["identifier"] == "192.168.1.100"


@set_metadata(
    integration_config=common.CONFIG,
    parameters=POLLING_PARAMS,
    entities=[IP_ENTITY],
    input_context={
        "async_total_duration_deadline": int(
            SCRIPT_DEADLINE_TIME.timestamp() * NUM_OF_MILLI_IN_SEC
        )
    },
)
def test_download_file_polling_completed_success(
    palo_alto_cortex_xdr: PaloAltoCortexXDR,
    action_output: MockActionOutput,
) -> None:
    """Test polling completion run downloading files and attaching them to entity."""
    mock_calc_bytes: bytes = b"FakeCalcBytes"
    mock_passwd_bytes: bytes = b"FakePasswdBytes"

    palo_alto_cortex_xdr.add_file_content_by_val("mysecrettoken", mock_calc_bytes)
    palo_alto_cortex_xdr.add_file_content_by_val("tokenpasswd", mock_passwd_bytes)

    palo_alto_cortex_xdr.add_file_retrieval(
        common.GROUP_ID_CALC, {"data": {common.ENDPOINT_ID: "COMPLETED_SUCCESSFULLY"}}
    )
    palo_alto_cortex_xdr.add_file_retrieval(
        common.GROUP_ID_PASSWD, {"data": {common.ENDPOINT_ID: "COMPLETED_SUCCESSFULLY"}}
    )

    palo_alto_cortex_xdr.add_file_retrieval_urls(
        group_action_id=common.GROUP_ID_CALC, urls=common.RETRIEVAL_DETAILS
    )
    palo_alto_cortex_xdr.add_file_retrieval_urls(
        group_action_id=common.GROUP_ID_PASSWD, urls=common.RETRIEVAL_DETAILS_PASSWD
    )

    if os.path.exists(TEST_DOWNLOAD_DIR_POLLING):
        shutil.rmtree(TEST_DOWNLOAD_DIR_POLLING)
    os.makedirs(TEST_DOWNLOAD_DIR_POLLING)

    DownloadFile.main()

    assert action_output.results.execution_state == ExecutionState.COMPLETED
    assert action_output.results.result_value is True
    assert SUCCESS_OUTPUT_MESSAGE in action_output.results.output_message

    expected_calc_file: str = os.path.join(
        TEST_DOWNLOAD_DIR_POLLING,
        f"{common.ENTITY_IDENTIFIER}-C_Windows_System32_calc.exe.zip",
    )
    expected_passwd_file: str = os.path.join(
        TEST_DOWNLOAD_DIR_POLLING, f"{common.ENTITY_IDENTIFIER}-etc_passwd.zip"
    )

    assert os.path.exists(expected_calc_file)
    assert os.path.exists(expected_passwd_file)

    with open(expected_calc_file, "rb") as f:
        assert f.read() == mock_calc_bytes
    with open(expected_passwd_file, "rb") as f:
        assert f.read() == mock_passwd_bytes
