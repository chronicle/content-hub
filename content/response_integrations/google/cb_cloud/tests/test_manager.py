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

"""Unit tests for CBCloud Integration."""
import json
import os
import pytest
from pytest_mock import MockerFixture

from cb_cloud.core import CBCloudManager
from integration_testing.logger import Logger
import requests

# Constants
MOCK_DATA = json.load(
    open(
        os.path.join(os.path.dirname(__file__), "mock_data.json")
    )
)

ALERTS = MOCK_DATA.get('alerts')
SEARCH_DEVICES = MOCK_DATA.get('search_devices')
EVENT_DATA = MOCK_DATA.get('get_event_by_job_id')
DETAILED_EVENT_DATA = MOCK_DATA.get('get_detailed_events_by_job_id')
CREATE_JOB_PROCESS = MOCK_DATA.get('create_job_for_search_process')
DEVICE_ID = 5765373
JOB_ID = 'c9933283-2b61-4433-9f73-13d58941a41a-sqs'

@pytest.fixture
def cbmanager():
    """Return CBCloudManager manager instance"""
    logger = Logger()
    with open(os.path.join(os.path.dirname(__file__), "config.json"), "r") as f:
        data = f.read()

    config = json.loads(data)

    api_root = (
        config.get('API Root') if config.get('API Root') is not None
        else 'https://mockhost:8443/cbcloud'
    )
    org_key = config.get('Organization Key')
    api_id = config.get('API ID')
    api_secret_key = config.get('API Secret Key')
    verify_ssl = config.get('Verify SSL')

    manager = CBCloudManager.CBCloudManager(
        api_root=api_root,
        org_key=org_key,
        api_id=api_id,
        api_secret_key=api_secret_key,
        verify_ssl=verify_ssl
    )

    return manager


class TestCBCloudManager:
    """Unit tests for CBCloudManager's functions Integration."""

    def test_test_connectivity_valid_success(
        self,
        mocker: MockerFixture,
        cbmanager: CBCloudManager
    ) -> None:
        mock_post = mocker.Mock()
        mock_post.json.return_value = {}
        mock_post.raise_for_status.return_value = False

        mocker.patch.object(cbmanager.session, 'post', return_value=mock_post)

        result = cbmanager.test_connectivity()

        assert result is True

    def test_test_connectivity_invalid_response_code_401_raise_exception(
        self,
        mocker: MockerFixture,
        cbmanager: CBCloudManager
    ) -> None:
        mock_post = mocker.Mock()
        mock_post.json.return_value = {}
        mock_post.raise_for_status.return_value = False
        mock_post.status_code = 401

        mocker.patch.object(cbmanager.session, 'post', return_value=mock_post)

        with pytest.raises(Exception) as error:
            cbmanager.test_connectivity()

        assert type(error.value).__name__ == 'CBCloudUnauthorizedError'
        assert 'Unauthorized. Please check given credentials.' in str(
            error.value
        )

    def test_test_connectivity_invalid_response_code_404_raise_exception(
        self,
        mocker: MockerFixture,
        cbmanager: CBCloudManager
    ) -> None:
        mock_post = mocker.Mock()
        mock_post.json.return_value = {
            'error_code': 'NOT_FOUND',
            'resource_type': 'org'
        }
        mock_post.raise_for_status.return_value = False
        mock_post.status_code = 404

        mocker.patch.object(cbmanager.session, 'post', return_value=mock_post)

        with pytest.raises(Exception) as error:
            cbmanager.test_connectivity()

        assert type(error.value).__name__ == 'CBCloudUnauthorizedError'
        assert 'Invalid organization ID.' in str(error.value)

    def test_test_connectivity_invalid_response_code_raise_exception(
        self,
        mocker: MockerFixture,
        cbmanager: CBCloudManager
    ) -> None:
        mock_post = mocker.Mock()
        mock_post.content = 'Some 503 mocking error'
        mock_post.raise_for_status.side_effect = requests.HTTPError(
            'An error occurred.'
        )
        mock_post.status_code = 503

        mocker.patch.object(cbmanager.session, 'post', return_value=mock_post)

        with pytest.raises(Exception) as error:
            cbmanager.test_connectivity()

        assert type(error.value).__name__ == 'CBCloudException'
        assert 'Some 503 mocking error' in str(error.value)

    def test_dismiss_alert_valid_success(
        self,
        mocker: MockerFixture,
        cbmanager: CBCloudManager
    ) -> None:
        alert_id = '1234'
        remediation_state = 'SUCCESS'
        determination = 'None'
        mock_post = mocker.Mock()
        mock_post.json.return_value = {}
        mock_post.raise_for_status.return_value = False

        mocker.patch.object(cbmanager.session, 'post', return_value=mock_post)

        result = cbmanager.dismiss_alert(alert_id, remediation_state, determination)

        assert result is True

    def test_search_devices_valid_success(
        self,
        mocker: MockerFixture,
        cbmanager: CBCloudManager
    ) -> None:
        mock_pagination = mocker.Mock()
        mock_pagination.return_value = cbmanager.parser.get_results(
            SEARCH_DEVICES
        )
        mocker.patch.object(cbmanager, '_paginate_results', mock_pagination)

        result = cbmanager.search_devices()

        # assert
        assert len(result) == 3
        # assertdatamodels.Device object is exist.
        assert 'Device' in type(result[0]).__name__

    def test_get_devices_by_name_valid_success(
        self,
        mocker: MockerFixture,
        cbmanager: CBCloudManager
    ) -> None:
        mock_pagination = mocker.Mock()
        mock_pagination.return_value = cbmanager.parser.get_results(
            SEARCH_DEVICES
        )
        mocker.patch.object(cbmanager, '_paginate_results', mock_pagination)

        result = cbmanager.get_devices_by_name(starts_with_name='carbonblack')

        # assert
        assert len(result) == 1
        # assertdatamodels.Device object is exist.
        assert 'Device' in type(result[0]).__name__

    def test_get_devices_valid_success(
        self,
        mocker: MockerFixture,
        cbmanager: CBCloudManager
    ) -> None:
        mock_pagination = mocker.Mock()
        mock_pagination.return_value = cbmanager.parser.get_results(
            SEARCH_DEVICES
        )
        mocker.patch.object(cbmanager, '_paginate_results', mock_pagination)

        result = cbmanager.get_devices()

        # assert
        assert len(result) == 3
        # assertdatamodels.Device object is exist.
        assert 'Device' in type(result[0]).__name__

    def test_create_policy_update_task_valid_success(
        self,
        mocker: MockerFixture,
        cbmanager: CBCloudManager
    ) -> None:
        policy_id = 6525
        mock_post = mocker.Mock()
        mock_post.json.return_value = SEARCH_DEVICES
        mock_post.status_code = 204

        mocker.patch.object(cbmanager.session, 'post', return_value=mock_post)

        result = cbmanager.create_policy_update_task(DEVICE_ID, policy_id)

        # assert
        assert result is True

    def test_create_policy_update_task_invalid_policy_raise_exception(
        self,
        mocker: MockerFixture,
        cbmanager: CBCloudManager
    ) -> None:
        policy_id = 'default'
        mock_post = mocker.Mock()
        mock_post.json.return_value = MOCK_DATA.get("update_policy_error")
        mock_post.status_code = 400
        mock_post.raise_for_status.side_effect = requests.HTTPError(
            '400 Client Error: Bad Request for url:'
        )

        mocker.patch.object(cbmanager.session, 'post', return_value=mock_post)
        with pytest.raises(Exception) as error:
            cbmanager.create_policy_update_task(DEVICE_ID, policy_id)

        # assert
        assert type(error.value).__name__ == 'CBCloudException'
        assert 'Unable to create policy update task for device' in str(
            error.value
        )

    def test_create_quarantine_task_valid_success(
        self,
        mocker: MockerFixture,
        cbmanager: CBCloudManager
    ) -> None:
        mock_post = mocker.Mock()
        mock_post.json.return_value = SEARCH_DEVICES
        mock_post.status_code = 204

        mocker.patch.object(cbmanager.session, 'post', return_value=mock_post)

        result = cbmanager.create_quarantine_task(DEVICE_ID)

        # assert
        assert result is True

    def test_create_quarantine_task_invalid_policy_raise_exception(
        self,
        mocker: MockerFixture,
        cbmanager: CBCloudManager
    ) -> None:
        mock_post = mocker.Mock()
        mock_post.status_code = 400
        mock_post.json.return_value = MOCK_DATA.get('update_policy_error')
        mock_post.raise_for_status.side_effect = requests.HTTPError(
            '400 Client Error: Bad Request for url:'
        )

        mocker.patch.object(cbmanager.session, 'post', return_value=mock_post)
        with pytest.raises(Exception) as error:
            cbmanager.create_quarantine_task(DEVICE_ID)

        # assert
        assert type(error.value).__name__ == 'CBCloudException'
        assert (
            f'Unable to create quarantine task for device {DEVICE_ID}' in str(
                error.value
            )
        )

    def test_create_unquarantine_task_valid_success(
        self,
        mocker: MockerFixture,
        cbmanager: CBCloudManager
    ) -> None:
        mock_post = mocker.Mock()
        mock_post.json.return_value = SEARCH_DEVICES
        mock_post.status_code = 204

        mocker.patch.object(cbmanager.session, 'post', return_value=mock_post)

        result = cbmanager.create_unquarantine_task(DEVICE_ID)

        # assert
        assert result is True

    def test_create_unquarantine_task_invalid_policy_raise_exception(
        self,
        mocker: MockerFixture,
        cbmanager: CBCloudManager
    ) -> None:
        mock_post = mocker.Mock()
        mock_post.status_code = 400
        mock_post.json.return_value = MOCK_DATA.get('update_policy_error')
        mock_post.raise_for_status.side_effect = requests.HTTPError(
            '400 Client Error: Bad Request for url:'
        )

        mocker.patch.object(cbmanager.session, 'post', return_value=mock_post)
        with pytest.raises(Exception) as error:
            cbmanager.create_unquarantine_task(DEVICE_ID)

        # assert
        assert type(error.value).__name__ == 'CBCloudException'
        assert (
            f'Unable to create unquarantine task for device {DEVICE_ID}' in str(
                error.value
            )
        )

    def test_create_enable_bypass_mode_task_valid_success(
        self,
        mocker: MockerFixture,
        cbmanager: CBCloudManager
    ) -> None:
        mock_post = mocker.Mock()
        mock_post.json.return_value = SEARCH_DEVICES
        mock_post.status_code = 204

        mocker.patch.object(cbmanager.session, 'post', return_value=mock_post)

        result = cbmanager.create_enable_bypass_mode_task(DEVICE_ID)

        # assert
        assert result is True

    def test_create_enable_bypass_mode_task_invalid_policy_raise_exception(
        self,
        mocker: MockerFixture,
        cbmanager: CBCloudManager
    ) -> None:
        mock_post = mocker.Mock()
        mock_post.status_code = 400
        mock_post.json.return_value = MOCK_DATA.get('update_policy_error')
        mock_post.raise_for_status.side_effect = requests.HTTPError(
            '400 Client Error: Bad Request for url:'
        )

        mocker.patch.object(cbmanager.session, 'post', return_value=mock_post)
        with pytest.raises(Exception) as error:
            cbmanager.create_enable_bypass_mode_task(DEVICE_ID)

        # assert
        assert type(error.value).__name__ == 'CBCloudException'
        assert (
            f'Unable to create enable bypass mode task for device {DEVICE_ID}'
            in str(
                error.value
            )
        )

    def test_create_disable_bypass_mode_task_valid_success(
        self,
        mocker: MockerFixture,
        cbmanager: CBCloudManager
    ) -> None:
        mock_post = mocker.Mock()
        mock_post.json.return_value = SEARCH_DEVICES
        mock_post.status_code = 204

        mocker.patch.object(cbmanager.session, 'post', return_value=mock_post)

        result = cbmanager.create_disable_bypass_mode_task(DEVICE_ID)

        # assert
        assert result is True

    def test_create_disable_bypass_mode_task_invalid_policy_raise_exception(
        self,
        mocker: MockerFixture,
        cbmanager: CBCloudManager
    ) -> None:
        mock_post = mocker.Mock()
        mock_post.status_code = 400
        mock_post.json.return_value = MOCK_DATA.get('update_policy_error')
        mock_post.raise_for_status.side_effect = requests.HTTPError(
            '400 Client Error: Bad Request for url:'
        )

        mocker.patch.object(cbmanager.session, 'post', return_value=mock_post)
        with pytest.raises(Exception) as error:
            cbmanager.create_disable_bypass_mode_task(DEVICE_ID)

        # assert
        assert type(error.value).__name__ == 'CBCloudException'
        assert (
            f'Unable to create disable bypass mode task for device {DEVICE_ID}'
            in str(
                error.value
            )
        )

    def test_create_background_scan_task_valid_success(
        self,
        mocker: MockerFixture,
        cbmanager: CBCloudManager
    ) -> None:
        mock_post = mocker.Mock()
        mock_post.json.return_value = SEARCH_DEVICES
        mock_post.status_code = 204

        mocker.patch.object(cbmanager.session, 'post', return_value=mock_post)

        result = cbmanager.create_background_scan_task(DEVICE_ID)

        # assert
        assert result is True

    def test_create_background_scan_task_invalid_policy_raise_exception(
        self,
        mocker: MockerFixture,
        cbmanager: CBCloudManager
    ) -> None:
        mock_post = mocker.Mock()
        mock_post.status_code = 400
        mock_post.json.return_value = MOCK_DATA.get('update_policy_error')
        mock_post.raise_for_status.side_effect = requests.HTTPError(
            '400 Client Error: Bad Request for url:'
        )

        mocker.patch.object(cbmanager.session, 'post', return_value=mock_post)
        with pytest.raises(Exception) as error:
            cbmanager.create_background_scan_task(DEVICE_ID)

        # assert
        assert type(error.value).__name__ == 'CBCloudException'
        assert (
            f"Unable to create background scan task for device {DEVICE_ID}"
            in str(
                error.value
            )
        )

    def test_get_alerts_valid_success(
        self,
        mocker: MockerFixture,
        cbmanager: CBCloudManager
    ) -> None:
        mock_pagination = mocker.Mock()
        mock_pagination.return_value = cbmanager.parser.get_results(ALERTS)
        start_time = '2024-05-19T07:41:06.165821+00:00'
        end_time = '2024-05-20T07:41:06.166233+00:00'

        mocker.patch.object(cbmanager, '_paginate_results', mock_pagination)

        result = cbmanager.get_alerts(
            start_time=start_time, end_time=end_time, limit=10
        )

        # assert
        assert len(result) == 3
        assert 'Alert' in type(result[0]).__name__

    def test_get_alerts_by_id_valid_success(
        self,
        mocker: MockerFixture,
        cbmanager: CBCloudManager
    ) -> None:
        mock_post = mocker.Mock()
        mock_post.json.return_value = ALERTS

        mocker.patch.object(cbmanager.session, 'post', return_value=mock_post)

        result = cbmanager.get_alerts_by_id(
            ids='fcf62abf-0f52-4124-87d9-e9cc53c2c8de',
            limit=10
        )

        # assert
        assert len(result) == 3
        assert 'Alert' in type(result[0]).__name__

    def test_get_updated_alerts_valid_success(
        self,
        mocker: MockerFixture,
        cbmanager: CBCloudManager
    ) -> None:
        mock_pagination = mocker.Mock()
        mock_pagination.return_value = cbmanager.parser.get_results(ALERTS)

        mocker.patch.object(cbmanager, '_paginate_results', mock_pagination)

        result = cbmanager.get_updated_alerts(limit=10)

        # assert
        assert len(result) == 3
        assert 'Alert' in type(result[0]).__name__

    def test_get_events_by_job_id_valid_success(
        self,
        mocker: MockerFixture,
        cbmanager: CBCloudManager
    ) -> None:
        mock_get = mocker.Mock()
        mock_get.json.return_value = EVENT_DATA

        mocker.patch.object(
            cbmanager, 'is_search_process_completed', return_value=True
        )
        mocker.patch.object(cbmanager.session, 'get', return_value=mock_get)

        result = cbmanager.get_events_by_job_id(JOB_ID)

        # assert
        assert 'Event' in type(result).__name__

    def test_get_events_by_process_name_valid_success(
        self,
        mocker: MockerFixture,
        cbmanager: CBCloudManager
    ) -> None:
        mock_post = mocker.Mock()
        mock_get = mocker.Mock()
        mock_post.json.return_value = CREATE_JOB_PROCESS
        mock_get.json.return_value = EVENT_DATA

        mocker.patch.object(
            cbmanager, 'is_search_process_completed', return_value=True
        )
        mocker.patch.object(cbmanager.session, 'post', return_value=mock_post)
        mocker.patch.object(cbmanager.session, 'get', return_value=mock_get)

        result = cbmanager.get_events_by_process_name(JOB_ID, 'HOSTNAME')

        # assert
        assert 'Event' in type(result).__name__

    def test_get_detailed_events_information_valid_success(
        self,
        mocker: MockerFixture,
        cbmanager: CBCloudManager
    ) -> None:
        process_guids = ["7DESJ9GN-0057f8fd-00001844-00000000-1d998d24114134e"]
        mock_post = mocker.Mock()
        mock_get = mocker.Mock()
        mock_post.json.return_value = CREATE_JOB_PROCESS
        mock_get.json.return_value = DETAILED_EVENT_DATA

        mocker.patch.object(cbmanager.session, 'post', return_value=mock_post)
        mocker.patch.object(cbmanager.session, 'get', return_value=mock_get)
        result = cbmanager.get_detailed_events_information(process_guids)

        # assert
        assert 'DetailedEvent' in type(result).__name__

    def test_get_events_by_alert_id_valid_success(
        self,
        mocker: MockerFixture,
        cbmanager: CBCloudManager
    ) -> None:
        alert_id = "mock_alert_id"
        mock_post = mocker.Mock()
        mock_get = mocker.Mock()
        mock_post.json.return_value = CREATE_JOB_PROCESS
        mock_get.json.return_value = DETAILED_EVENT_DATA

        mocker.patch.object(cbmanager.session, 'post', return_value=mock_post)
        mocker.patch.object(cbmanager.session, 'get', return_value=mock_get)

        result = cbmanager.get_events_by_alert_id(alert_id)

        # assert
        assert len(result) == 2
        assert 'EnrichedEvent' in type(result[0]).__name__

    def test_check_search_status_and_get_results_valid_success(
        self,
        mocker: MockerFixture,
        cbmanager: CBCloudManager
    ) -> None:
        mock_get = mocker.Mock()
        mock_get.json.return_value = DETAILED_EVENT_DATA

        mocker.patch.object(cbmanager.session, 'get', return_value=mock_get)

        result = cbmanager.check_search_status_and_get_results(JOB_ID)

        # assert
        assert isinstance(result, tuple)
        assert 'EnrichedEvent' in type(result[0][0]).__name__
        assert result[1] == 2

    def test_check_search_status_and_get_results_invalid_success(
        self,
        mocker: MockerFixture,
        cbmanager: CBCloudManager
    ) -> None:
        default_completed_value = DETAILED_EVENT_DATA['completed']
        DETAILED_EVENT_DATA['completed'] = 1
        mock_get = mocker.Mock()
        mock_get.json.return_value = DETAILED_EVENT_DATA

        mocker.patch.object(cbmanager.session, 'get', return_value=mock_get)

        result = cbmanager.check_search_status_and_get_results(JOB_ID)

        # assert
        assert result == (None, None)
        DETAILED_EVENT_DATA['completed'] = default_completed_value

    def test_check_detailed_search_status_and_get_results_valid_success(
        self,
        mocker: MockerFixture,
        cbmanager: CBCloudManager
    ) -> None:
        mock_get = mocker.Mock()
        mock_get.json.return_value = DETAILED_EVENT_DATA

        mocker.patch.object(cbmanager.session, 'get', return_value=mock_get)

        result = cbmanager.check_detailed_search_status_and_get_results(JOB_ID)

        # assert
        assert isinstance(result, list)
        assert 'EnrichedEvent' in type(result[0]).__name__

    def test_check_detailed_search_status_and_get_results_invalid_success(
        self,
        mocker: MockerFixture,
        cbmanager: CBCloudManager
    ) -> None:
        default_completed_value = DETAILED_EVENT_DATA['completed']
        DETAILED_EVENT_DATA['completed'] = 1
        mock_get = mocker.Mock()
        mock_get.json.return_value = DETAILED_EVENT_DATA

        mocker.patch.object(cbmanager.session, 'get', return_value=mock_get)

        result = cbmanager.check_detailed_search_status_and_get_results(JOB_ID)

        # assert
        assert result is None
        DETAILED_EVENT_DATA['completed'] = default_completed_value

    def test_get_events_detailed_information_valid_success(
        self,
        mocker: MockerFixture,
        cbmanager: CBCloudManager
    ) -> None:
        mock_post = mocker.Mock()
        mock_get = mocker.Mock()
        mock_post.json.return_value = CREATE_JOB_PROCESS
        mock_get.json.return_value = DETAILED_EVENT_DATA

        mocker.patch.object(cbmanager.session, 'post', return_value=mock_post)
        mocker.patch.object(cbmanager.session, 'get', return_value=mock_get)

        result = cbmanager.get_events_detailed_information(
            event_ids=['mock_id1', 'mock_id2']
        )

        # assert
        assert 'EnrichedEvent' in type(result[0]).__name__

    def test_get_events_detailed_information_empty_event_ids_success(
        self,
        mocker: MockerFixture,
        cbmanager: CBCloudManager
    ) -> None:

        result = cbmanager.get_events_detailed_information(
            event_ids=[]
        )

        # assert
        assert result == []