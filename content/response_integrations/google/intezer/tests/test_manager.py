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
        intezer_manager.http_client = mocker.Mock()
        intezer_manager.http_client.request.return_value = IntezerAPIResponse(
            response_info=const.DUMMY_CONTENT,
            content=custom_response.data,
        )

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
        intezer_manager.http_client = mocker.Mock()
        intezer_manager.http_client.request.return_value = IntezerAPIResponse(
            response_info=const.DUMMY_CONTENT_CREATED,
            content=json.dumps(custom_response.data),
        )
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
        intezer_manager.http_client = mocker.Mock()
        intezer_manager.http_client.request.return_value = IntezerAPIResponse(
            response_info=const.DUMMY_CONTENT_CREATED,
            content=json.dumps(custom_response.data),
        )
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
        intezer_manager.http_client = mocker.Mock()
        intezer_manager.http_client.request.return_value = IntezerAPIResponse(
            response_info=const.DUMMY_CONTENT_CREATED,
            content=json.dumps(custom_response.data),
        )
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
        intezer_manager.http_client = mocker.Mock()
        intezer_manager.http_client.request.return_value = IntezerAPIResponse(
            response_info=const.DUMMY_CONTENT_CREATED,
            content=json.dumps(custom_response.data),
        )
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
        intezer_manager.http_client = mocker.Mock()
        intezer_manager.http_client.request.return_value = IntezerAPIResponse(
            response_info=const.DUMMY_CONTENT_CREATED,
            content=json.dumps(custom_response.data),
        )
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
        intezer_manager.http_client = mocker.Mock()
        intezer_manager.http_client.request.return_value = IntezerAPIResponse(
            response_info=const.DUMMY_CONTENT_CREATED,
            content=json.dumps(custom_response.data),
        )
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
        intezer_manager.http_client = mocker.Mock()
        intezer_manager.http_client.request.return_value = IntezerAPIResponse(
            response_info=const.DUMMY_CONTENT_CREATED,
            content=json.dumps(custom_response.data),
        )
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
        intezer_manager.http_client = mocker.Mock()
        intezer_manager.http_client.request.return_value = IntezerAPIResponse(
            response_info=const.DUMMY_CONTENT_CREATED,
            content=json.dumps(custom_response.data),
        )
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
        intezer_manager.http_client = mocker.Mock()
        intezer_manager.http_client.request.return_value = IntezerAPIResponse(
            response_info=const.DUMMY_CONTENT_CREATED,
            content=json.dumps(custom_response.data),
        )
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
        intezer_manager.http_client = mocker.Mock()
        intezer_manager.http_client.request.return_value = IntezerAPIResponse(
            response_info=const.DUMMY_CONTENT_CREATED,
            content=json.dumps(custom_response.data),
        )
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
        intezer_manager.http_client = mocker.Mock()
        intezer_manager.http_client.request.return_value = IntezerAPIResponse(
            response_info=const.DUMMY_CONTENT_CREATED,
            content=json.dumps(custom_response.data),
        )
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
        intezer_manager.http_client = mocker.Mock()
        intezer_manager.http_client.request.return_value = IntezerAPIResponse(
            response_info=const.DUMMY_CONTENT_CREATED,
            content=json.dumps(custom_response.data),
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

        dir_path = os.path.dirname(os.path.realpath(__file__))
        with open(os.path.join(dir_path, file_name), "r", encoding="utf-8") as f:
            response = json.load(f)
        return response
