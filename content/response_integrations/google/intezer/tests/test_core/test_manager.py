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

"""Unit tests for Intezer Integration."""
from collections import namedtuple
import json
import os
import pytest
from pytest_mock import MockerFixture

from TIPCommon.types import JSON

from intezer.core.constants import (
    IndexType,
)
from intezer.core.IntezerManager import (
    IntezerManager,
)
from intezer.core.exceptions import (
    IntezerManagerError,
)
from intezer.tests import const
IntezerAPIResponse = namedtuple(
    "IntezerAPIResponse",
    ["response_info", "content"],
)


class CustomReponse:
    """A class to represent a custom JSON response.

    Attributes:
        result (JSON): The internal storage for a JSON data

    Methods:
        data: Property that gets or sets the JSON data
    """

    def __init__(self,initial_data: JSON = None) -> None:
        """Consturcts a new CustomReponse object.

        Args:
            initial_data (JSON): An initial JSON data to store.
            Defaults to an empty dictionary.
        """
        self._result = initial_data or {}

    @property
    def data(self) -> JSON:
        """Returns the store JSON data.

        Returns:
            JSON: The store JSON data.
        """
        return self._result

    @data.setter
    def data(self, json_data: JSON):
        """Sets the JSON data

        Args:
            JSON: The store JSON data.
        """
        self._result = json_data


class TestIntezer:
    """Intezer test cases"""

    @staticmethod
    def _build_response(mocker: MockerFixture, payload: JSON, status_code: int = 200):
        resp = mocker.Mock()
        resp.status_code = status_code
        resp.json.return_value = payload
        resp.raise_for_status.return_value = None
        return resp

    def _mock_session(
        self,
        mocker: MockerFixture,
        intezer_manager: IntezerManager,
        payload: JSON,
        status_code: int = 200,
    ) -> None:
        resp = self._build_response(mocker, payload, status_code=status_code)
        intezer_manager.session.get.return_value = resp
        intezer_manager.session.post.return_value = resp
        intezer_manager.session.delete.return_value = resp

    def test_connectivity_success(
        self,
        mocker: MockerFixture,
        intezer_manager: IntezerManager
    ) -> None:
        """Test connectivity success.

        Args:
            mocker: MockerFixture
            intezer_manager: IntezerManager

        Returns:
            None
        """

        response_json = self.mock_get_response(
            "get_detonate_file.json"
        )
        custom_response = CustomReponse()
        custom_response.data = response_json
        self._mock_session(mocker, intezer_manager, custom_response.data, status_code=200)

        assert intezer_manager.test_connectivity() is None

    def test_get_detonate_file(
        self,
        mocker: MockerFixture,
        intezer_manager: IntezerManager
    ) -> None:
        """Test the get_detonate_file success

        Args:
            mocker: MockerFixture
            intezer_manager: IntezerManager

        Raises:
            AssertionError: If the result does not match
            the expected data.

        Returns:
            None
        """
        response_json = self.mock_get_response(
            "get_detonate_file.json"
        )
        custom_response = CustomReponse()
        custom_response.data = response_json
        self._mock_session(mocker, intezer_manager, custom_response.data, status_code=const.STATUS_CODE)
        result = intezer_manager.get_detonate_file(
            file_path=const.FILE_NAME,
            related_alert_ids=const.DEFAULT_VALUE
        )
        assert result is not None
        assert result.analysis_status == const.CREATED_STATUS
        assert result.identifier == const.FILE_NAME

    def test_is_analysis_completed(
        self,
        mocker: MockerFixture,
        intezer_manager: IntezerManager
    ) -> None:
        """Test the is_analysis_completed success

        Args:
            mocker: MockerFixture
            intezer_manager: IntezerManager

        Raises:
            AssertionError: If the result does not match
            the expected data.

        Returns:
            None
        """
        response_json = self.mock_get_response(
            "submit_hash.json"
        )
        custom_response = CustomReponse()
        custom_response.data = response_json
        self._mock_session(mocker, intezer_manager, custom_response.data, status_code=200)
        existing_results = intezer_manager.is_analysis_completed(const.RESULT_URL)
        if existing_results:
            report = intezer_manager.get_results(const.RESULT_URL)
            assert (
                report.get("verdict")
                == custom_response.data.get("result").get("verdict")
            )

    def test_submit_hash(
        self,
        mocker: MockerFixture,
        intezer_manager: IntezerManager
    ) -> None:
        """Test the submit_hash success

        Args:
            mocker: MockerFixture
            intezer_manager: IntezerManager

        Raises:
            AssertionError: If the result does not match
            the expected data.

        Returns:
            None
        """
        response_json = self.mock_get_response(
            "submit_hash.json"
        )
        custom_response = CustomReponse()
        custom_response.data = response_json
        self._mock_session(mocker, intezer_manager, custom_response.data, status_code=200)
        existing_results = intezer_manager.get_existing_analysis(const.DETONATE_HASH)
        if existing_results:
            assert (
                existing_results.get("sha256")
                == custom_response.data.get("result").get("sha256")
            )
        else:
            result = intezer_manager.submit_hash(file_hash=const.DETONATE_HASH)
            assert result is not None

    def test_submit_alert(
        self,
        mocker: MockerFixture,
        intezer_manager: IntezerManager
    ) -> None:
        """Test the submit_alert success

        Args:
            mocker: MockerFixture
            intezer_manager: IntezerManager

        Raises:
            AssertionError: If the result does not match
            the expected data.

        Returns:
            None
        """
        response_json = self.mock_get_response(
            "submit_alert.json"
        )
        custom_response = CustomReponse()
        custom_response.data = response_json
        self._mock_session(mocker, intezer_manager, custom_response.data, status_code=const.STATUS_CODE)
        result = intezer_manager.submit_alert(
            alert_source=const.ALERT_SOURCE,
            alert_json=self.mock_get_response("raw_alert.json"),
            alert_mapping=self.mock_get_response("alert_mapping.json")
        )
        assert result is not None
        assert result.alert_id == custom_response.data.get("alert_id")

    def test_get_detonate_hash(
        self,
        mocker: MockerFixture,
        intezer_manager: IntezerManager
    ) -> None:
        """Test the get_detonate_hash success

        Args:
            mocker: MockerFixture
            intezer_manager: IntezerManager

        Raises:
            AssertionError: If the result does not match
            the expected data.

        Returns:
            None
        """
        response_json = self.mock_get_response(
            "get_detonate_hash.json"
        )
        custom_response = CustomReponse()
        custom_response.data = response_json
        self._mock_session(mocker, intezer_manager, custom_response.data, status_code=const.STATUS_CODE)
        result = intezer_manager.get_detonate_hash(
            detonate_hash=const.DETONATE_HASH
        )
        assert result is not None
        assert result.analysis_status == const.CREATED_STATUS
        assert result.identifier == const.DETONATE_HASH

    def test_unset_index_file(
        self,
        mocker: MockerFixture,
        intezer_manager: IntezerManager
    ) -> None:
        """Test the unset_index_file success

        Args:
            mocker: MockerFixture
            intezer_manager: IntezerManager

        Raises:
            AssertionError: If the result does not match
            the expected data.

        Returns:
            None
        """
        response_json = self.mock_get_response(
            "unset_index_file.json"
        )
        custom_response = CustomReponse()
        custom_response.data = response_json
        self._mock_session(mocker, intezer_manager, custom_response.data, status_code=const.STATUS_CODE)
        result = intezer_manager.unset_index_file(
            sha256=const.SHA256
        )
        assert result is not None
        assert result.status == const.STATUS_CODE

    def test_get_detonate_url(
        self,
        mocker: MockerFixture,
        intezer_manager: IntezerManager
    ) -> None:
        """Test the get_detonate_url success

        Args:
            mocker: MockerFixture
            intezer_manager: IntezerManager

        Raises:
            AssertionError: If the result does not match
            the expected data.

        Returns:
            None
        """
        response_json = self.mock_get_response(
            "get_detonate_url.json"
        )
        custom_response = CustomReponse()
        custom_response.data = response_json
        self._mock_session(mocker, intezer_manager, custom_response.data, status_code=const.STATUS_CODE)
        result = intezer_manager.get_detonate_url(
            detonate_url=const.DETONATE_URL
        )
        assert result is not None
        assert result.analysis_status == const.CREATED_STATUS
        assert result.identifier == const.DETONATE_URL

    def test_get_alert(
        self,
        mocker: MockerFixture,
        intezer_manager: IntezerManager
    ) -> None:
        """Test the get_alert success

        Args:
            mocker: MockerFixture
            intezer_manager: IntezerManager

        Raises:
            AssertionError: If the result does not match
            the expected data.

        Returns:
            None
        """
        response_json = self.mock_get_response(
            "get_alert.json"
        )
        custom_response = CustomReponse()
        custom_response.data = response_json
        self._mock_session(mocker, intezer_manager, custom_response.data, status_code=200)
        result = intezer_manager.get_alert(
            alert_id=const.ALERT_ID
        )
        assert result is not None
        assert result.status == const.SUCCESS_STATUS

    def test_get_url_report(
        self,
        mocker: MockerFixture,
        intezer_manager: IntezerManager
    ) -> None:
        """Test the get_url_report success

        Args:
            mocker: MockerFixture
            intezer_manager: IntezerManager

        Raises:
            AssertionError: If the result does not match
            the expected data.

        Returns:
            None
        """
        response_json = self.mock_get_response(
            "get_url_report.json"
        )
        custom_response = CustomReponse()
        custom_response.data = response_json
        self._mock_session(mocker, intezer_manager, custom_response.data, status_code=200)
        result = intezer_manager.get_url_report(
            analysis_id=const.URL_ANALYSIS_ID
        )
        assert result is not None
        assert result.status == const.SUCCESS_STATUS
        assert (
            result.to_json().get("analysis_id")
            == custom_response.data.get("result").get("analysis_id")
        )

    def test_get_file_report(
        self,
        mocker: MockerFixture,
        intezer_manager: IntezerManager
    ) -> None:
        """Test the get_file_report success

        Args:
            mocker: MockerFixture
            intezer_manager: IntezerManager

        Raises:
            AssertionError: If the result does not match
            the expected data.

        Returns:
            None
        """
        response_json = self.mock_get_response(
            "get_file_report.json"
        )
        custom_response = CustomReponse()
        custom_response.data = response_json
        intezer_manager.session.get.side_effect = [
            self._build_response(mocker, custom_response.data["analysis"]),
            self._build_response(mocker, custom_response.data["iocs"]),
            self._build_response(mocker, custom_response.data["dynamic-ttps"]),
            self._build_response(mocker, custom_response.data["sub-analyses"]),
            self._build_response(mocker, custom_response.data["metadata"]),
            self._build_response(mocker, {}),
        ]
        result = intezer_manager.get_file_report(
            analysis_id=const.ANALYSIS_ID,
            file_hash=const.DETONATE_HASH
        )
        assert result is not None
        assert result.status == const.SUCCESS_STATUS
        assert (
            result.analysis.get("analysis").get("analysis_id")
            == custom_response.data.get("analysis").get("result").get("analysis_id")
        )
        ioc_response = result.analysis.get("iocs").get("files")[0].get("sha256")
        ioc_mock = (
            custom_response.data.get("iocs").get("result").get("files")[0].get("sha256")
        )
        assert ioc_response == ioc_mock

    def test_submit_suspicious_email(
        self,
        mocker: MockerFixture,
        intezer_manager: IntezerManager
    ) -> None:
        """Test the submit_suspicious_email success

        Args:
            mocker: MockerFixture
            intezer_manager: IntezerManager

        Raises:
            AssertionError: If the result does not match
            the expected data.

        Returns:
            None
        """
        response_json = self.mock_get_response(
            "submit_suspicious_email.json"
        )
        custom_response = CustomReponse()
        custom_response.data = response_json
        self._mock_session(mocker, intezer_manager, custom_response.data, status_code=const.STATUS_CODE)
        result = intezer_manager.submit_suspicious_email(
            const.EMAIL_FILEPATH
        )
        assert result is not None
        assert result.alert_id == const.ALERT_ID
        assert result.raw_data == custom_response.data

    def test_get_index_id_from_file_hash(
        self,
        mocker: MockerFixture,
        intezer_manager: IntezerManager
    ) -> None:
        """Test the get_index_id_from_file_hash success

        Args:
            mocker: MockerFixture
            intezer_manager: IntezerManager

        Raises:
            AssertionError: If the result does not match
            the expected data.

        Returns:
            None
        """
        response_json = self.mock_get_response(
            "get_index_id_from_file_hash.json"
        )
        custom_response = CustomReponse()
        custom_response.data = response_json
        intezer_manager.session.post.return_value = self._build_response(
            mocker, custom_response.data, status_code=const.STATUS_CODE
        )
        intezer_manager.session.get.return_value = self._build_response(
            mocker, {"status": const.STATUS_IN_PROGRESS, "result": {}}, status_code=200
        )
        index_as = IndexType.from_str(const.TRUSTED)
        result = intezer_manager.get_index_id_from_file_hash(
            index_as=index_as,
            sha256=const.SHA256,
            family_name=const.DEFAULT_VALUE
        )
        response = intezer_manager.index_file_hash_by_id(index_id=result.id)
        assert response is not None
        assert response.status == const.STATUS_IN_PROGRESS

    @pytest.mark.usefixtures("mock_test_connectivity_to_raise_manager_error")
    def test_connectivity_failure(
        self,
        intezer_manager: IntezerManager
    ) -> None:
        """
        Test connectivity failure

        Args:
            intezer_manager: IntezerManager

        Returns:
            None

        Raises:
        - intezer_manager
        """

        with pytest.raises(IntezerManagerError):
            intezer_manager.test_connectivity()

    @pytest.mark.usefixtures("mock_get_file_report_to_raise_manager_error")
    def test_get_file_report_failure(
        self,
        intezer_manager: IntezerManager
    ) -> None:
        """Test get_file_report failure

        Args:
            intezer_manager: IntezerManager

        Returns:
            None

        Raises:
            IntezerManagerError
        """

        with pytest.raises(IntezerManagerError):
            intezer_manager.get_file_report(
                analysis_id=const.ANALYSIS_ID,
                file_hash=const.DETONATE_HASH
            )

    @pytest.mark.usefixtures("mock_submit_alert_to_raise_manager_error")
    def test_submit_alert_failure(
        self,
        intezer_manager: IntezerManager
    ) -> None:
        """Test submit_alert failure

        Args:
            intezer_manager: IntezerManager

        Returns:
            None

        Raises:
            IntezerManagerError
        """

        with pytest.raises(IntezerManagerError):
            intezer_manager.submit_alert(
                alert_source=const.ALERT_SOURCE,
                alert_json=self.mock_get_response("raw_alert.json"),
                alert_mapping=self.mock_get_response("alert_mapping.json")
            )

    @pytest.mark.usefixtures("mock_get_detonate_file_to_raise_manager_error")
    def test_get_detonate_file_failure(
        self,
        intezer_manager: IntezerManager
    ) -> None:
        """Test get_detonate_file failure

        Args:
            intezer_manager: IntezerManager

        Returns:
            None

        Raises:
            IntezerManagerError
        """

        with pytest.raises(IntezerManagerError):
            intezer_manager.get_detonate_file(
                file_path=const.FILE_NAME,
                related_alert_ids=const.DEFAULT_VALUE
            )

    @pytest.mark.usefixtures("mock_submit_suspicious_email_to_raise_manager_error")
    def test_submit_suspicious_email_failure(
        self,
        intezer_manager: IntezerManager
    ) -> None:
        """Test submit_suspicious_email failure

        Args:
            intezer_manager: IntezerManager

        Returns:
            None

        Raises:
            IntezerManagerError
        """

        with pytest.raises(IntezerManagerError):
            intezer_manager.submit_suspicious_email(const.EMAIL_FILEPATH)

    @pytest.mark.usefixtures("mock_get_alert_to_raise_manager_error")
    def test_get_alert_failure(
        self,
        intezer_manager: IntezerManager
    ) -> None:
        """Test get_alert failure

        Args:
            intezer_manager: IntezerManager

        Returns:
            None

        Raises:
            IntezerManagerError
        """

        with pytest.raises(IntezerManagerError):
            intezer_manager.get_alert(alert_id=const.ALERT_ID)

    @pytest.mark.usefixtures("mock_get_detonate_hash_to_raise_manager_error")
    def test_get_detonate_hash_failure(
        self,
        intezer_manager: IntezerManager
    ) -> None:
        """Test get_detonate_hash failure

        Args:
            intezer_manager: IntezerManager

        Returns:
            None

        Raises:
            IntezerManagerError
        """

        with pytest.raises(IntezerManagerError):
            intezer_manager.get_detonate_hash(
                detonate_hash=const.DETONATE_HASH
            )

    @pytest.mark.usefixtures("mock_get_detonate_url_to_raise_manager_error")
    def test_get_detonate_url_failure(
        self,
        intezer_manager: IntezerManager
    ) -> None:
        """Test get_detonate_url failure

        Args:
            intezer_manager: IntezerManager

        Returns:
            None

        Raises:
            IntezerManagerError
        """

        with pytest.raises(IntezerManagerError):
            intezer_manager.get_detonate_url(detonate_url=const.DETONATE_URL)

    @pytest.mark.usefixtures("mock_get_index_id_from_file_hash_to_raise_manager_error")
    def test_get_index_id_from_file_hash_failure(
        self,
        intezer_manager: IntezerManager
    ) -> None:
        """Test get_index_id_from_file_hash failure

        Args:
            intezer_manager: IntezerManager

        Returns:
            None

        Raises:
            IntezerManagerError
        """

        with pytest.raises(IntezerManagerError):
            index_as = IndexType.from_str(const.TRUSTED)
            result = intezer_manager.get_index_id_from_file_hash(
                index_as=index_as,
                sha256=const.SHA256,
                family_name=const.DEFAULT_VALUE
            )
            intezer_manager.index_file_hash_by_id(index_id=result.id)

    @pytest.mark.usefixtures("mock_unset_index_file_to_raise_manager_error")
    def test_unset_index_file_failure(
        self,
        intezer_manager: IntezerManager
    ) -> None:
        """Test unset_index_file failure

        Args:
            intezer_manager: IntezerManager

        Returns:
            None

        Raises:
            IntezerManagerError
        """

        with pytest.raises(IntezerManagerError):
            intezer_manager.unset_index_file(sha256=const.SHA256)

    @pytest.mark.usefixtures("mock_get_url_report_to_raise_manager_error")
    def test_get_url_report_failure(
        self,
        intezer_manager: IntezerManager
    ) -> None:
        """Test get_url_report failure

        Args:
            intezer_manager: IntezerManager

        Returns:
            None

        Raises:
            IntezerManagerError
        """

        with pytest.raises(IntezerManagerError):
            intezer_manager.get_url_report(analysis_id=const.URL_ANALYSIS_ID)

    @pytest.mark.usefixtures("mock_submit_hash_to_raise_manager_error")
    def test_submit_hash_failure(
        self,
        intezer_manager: IntezerManager
    ) -> None:
        """Test submit_hash failure

        Args:
            intezer_manager: IntezerManager

        Returns:
            None

        Raises:
            IntezerManagerError
        """

        with pytest.raises(IntezerManagerError):
            intezer_manager.submit_hash(file_hash=const.DETONATE_HASH)

    @pytest.mark.usefixtures("mock_is_analysis_completed_to_raise_manager_error")
    def test_is_analysis_completed_failure(
        self,
        intezer_manager: IntezerManager
    ) -> None:
        """Test is_analysis_completed failure

        Args:
            intezer_manager: IntezerManager

        Returns:
            None

        Raises:
            IntezerManagerError
        """

        with pytest.raises(IntezerManagerError):
            intezer_manager.is_analysis_completed(results_url=const.RESULT_URL)

    def mock_get_response(self, file_name: str) -> JSON:
        """Load and return JSON content from a given file in the
        same directory as th script.

        Parameters:
        File_name: The name of the file containing the JSON content.

        Returns:
        JSON: The parse JSON content of the file.

        Raises:
        FileNotFoundError: If the given file_name does not exist in the directory.
        json.JSONDecoderError: If the file content is not valid JSON.
        """

        dir_path = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
        with open(os.path.join(dir_path, file_name), "r", encoding="utf-8") as f:
            response = json.load(f)
        return response
