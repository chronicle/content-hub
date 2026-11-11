from __future__ import annotations

import json
import os

import pytest
from pytest_mock import MockerFixture
import requests

from connect_wise.core.ConnectWiseManager import ConnectWiseManager


# Constants
with open(
    os.path.join(os.path.dirname(__file__), "mock_data.json"), encoding="UTF-8"
) as wf:
    MOCK_DATA = json.load(wf)


STATUS_CODES = {
    "SUCCESS": 200,
    "BAD_REQUEST": 400,
    "UNAUTHORIZED": 401,
    "NOT_FOUND": 404,
    "CONFLICT": 409,
}


def mock_request(
    mocker: MockerFixture,
    method: str,
    request_string: str,
    response_code: int,
    exception: Exception | None = None,
) -> None:
    """Mock API request with desired api response and status code.

    Args:
        mocker (MockerFixture): MockerFixture object.
        method (str): method to patch.
        request_string (str): json response string to get from mock_data.
        response_code (int): api response status code to mock.
        exception (Exception | None, optional): Exception in case invalid test cases.
    """
    mock_response_data = MOCK_DATA.get(request_string)
    mock_data = mocker.MagicMock()
    mock_data.status_code = response_code
    mock_data.json.return_value = mock_response_data
    mock_data.text = mock_response_data if isinstance(mock_response_data, str) else None
    mock_data.raise_for_status.side_effect = None if exception is None else exception
    mocker.patch.object(requests.Session, method.lower(), return_value=mock_data)


class TestConnectWiseManager:
    """Unit tests for GoogleCloudArmorManager's functions Integration."""

    def test_test_connectivity_valid_success(
        self,
        mocker: MockerFixture,
        api_manager: ConnectWiseManager,
    ) -> None:
        # Arrange
        mock_request(
            mocker,
            method="GET",
            request_string="test_connectivity",
            response_code=STATUS_CODES.get("SUCCESS"),
        )

        # Act
        result = api_manager.test_connectivity()

        # Assert
        assert result is True

    def test_test_connectivity_invalid_valid_failure(
        self,
        mocker: MockerFixture,
        api_manager: ConnectWiseManager,
    ) -> None:
        # Arrange
        expected_mock_data = MOCK_DATA.get("test_connectivity_invalid")
        mock_request(
            mocker,
            method="GET",
            request_string="test_connectivity_invalid",
            response_code=STATUS_CODES.get("UNAUTHORIZED"),
            exception=requests.HTTPError(expected_mock_data),
        )

        # Act
        with pytest.raises(Exception) as err:
            api_manager.test_connectivity()

        # Assert
        assert err.typename == "ConnectWiseManagerError"
        assert expected_mock_data in str(err.value)

    def test_create_ticket_valid_success(
        self,
        mocker: MockerFixture,
        api_manager: ConnectWiseManager,
    ) -> None:
        # Arrange
        mock_request(
            mocker,
            method="POST",
            request_string="ticket_valid",
            response_code=STATUS_CODES.get("SUCCESS"),
        )
        mocker.patch.object(api_manager, "get_status_id_by_name", return_value="16")
        mocker.patch.object(api_manager, "get_priority_id_by_name", return_value="4")

        # Act
        result = api_manager.create_ticket(
            summary="mock_summary",
            company="mock_company",
            board="mock_board",
            status_name="mock_status",
            priority_name="mock_priority",
        )

        # Assert
        assert result == "674"
        assert isinstance(result, str)

    def test_create_ticket_invalid_company_failure(
        self,
        mocker: MockerFixture,
        api_manager: ConnectWiseManager,
    ) -> None:
        # Arrange
        expected_mock_data = MOCK_DATA.get("ticket_invalid")["errors"][0]
        mock_request(
            mocker,
            method="POST",
            request_string="ticket_invalid",
            response_code=STATUS_CODES.get("BAD_REQUEST"),
            exception=requests.HTTPError(expected_mock_data["message"]),
        )
        mocker.patch.object(api_manager, "get_status_id_by_name", return_value="16")
        mocker.patch.object(api_manager, "get_priority_id_by_name", return_value="4")

        # Act
        with pytest.raises(Exception) as err:
            api_manager.create_ticket(
                summary="mock_summary",
                company="invalid_company",
                board="mock_board",
                status_name="mock_status",
                priority_name="mock_priority",
            )

        # Assert
        assert err.typename == "ConnectWiseBadRequestError"
        assert expected_mock_data["message"] in str(err.value)

    def test_update_ticket_with_status_valid_success(
        self,
        mocker: MockerFixture,
        api_manager: ConnectWiseManager,
    ) -> None:
        # Arrange
        expected_mock_data = MOCK_DATA.get("ticket_valid")
        mock_request(
            mocker,
            method="PATCH",
            request_string="ticket_valid",
            response_code=STATUS_CODES.get("SUCCESS"),
        )
        mocker.patch.object(api_manager, "get_ticket", return_value=expected_mock_data)
        mocker.patch.object(api_manager, "get_status_id_by_name", return_value="16")

        # Act
        result = api_manager.update_ticket(ticket_id="674", status="mock_status")

        # Assert
        assert result == "674"
        assert isinstance(result, str)

    def test_update_ticket_without_status_valid_success(
        self,
        mocker: MockerFixture,
        api_manager: ConnectWiseManager,
    ) -> None:
        # Arrange
        mock_request(
            mocker,
            method="PATCH",
            request_string="ticket_valid",
            response_code=STATUS_CODES.get("SUCCESS"),
        )

        # Act
        result = api_manager.update_ticket(ticket_id="674")

        # Assert
        assert result == "674"
        assert isinstance(result, str)

    def test_update_ticket_status_valid_success(
        self,
        mocker: MockerFixture,
        api_manager: ConnectWiseManager,
    ) -> None:
        # Arrange
        expected_mock_data = MOCK_DATA.get("ticket_valid")
        mock_request(
            mocker,
            method="PATCH",
            request_string="ticket_valid",
            response_code=STATUS_CODES.get("SUCCESS"),
        )
        mocker.patch.object(api_manager, "get_ticket", return_value=expected_mock_data)
        mocker.patch.object(api_manager, "get_status_id_by_name", return_value="16")

        # Act
        result = api_manager.update_ticket_status(
            ticket_id="674",
            status="mock_status",
        )

        # Assert
        assert result == "674"
        assert isinstance(result, str)

    def test_close_ticket_valid_success(
        self,
        mocker: MockerFixture,
        api_manager: ConnectWiseManager,
    ) -> None:
        # Arrange
        expected_mock_data = MOCK_DATA.get("ticket_valid")
        mock_request(
            mocker,
            method="PATCH",
            request_string="close_ticket",
            response_code=STATUS_CODES.get("SUCCESS"),
        )
        mocker.patch.object(api_manager, "get_ticket", return_value=expected_mock_data)
        # Act
        result = api_manager.close_ticket(ticket_id="674")

        # Assert
        assert result == "674"
        assert isinstance(result, str)

    def test_close_ticket_with_custom_close_status_valid_success(
        self,
        mocker: MockerFixture,
        api_manager: ConnectWiseManager,
    ) -> None:
        # Arrange
        expected_mock_data = MOCK_DATA.get("ticket_valid")
        mock_request(
            mocker,
            method="PATCH",
            request_string="ticket_valid",
            response_code=STATUS_CODES.get("SUCCESS"),
        )
        mocker.patch.object(api_manager, "get_ticket", return_value=expected_mock_data)
        mocker.patch.object(api_manager, "get_status_id_by_name", return_value="16")

        # Act
        result = api_manager.close_ticket(ticket_id="674", custom_close_status=True)

        # Assert
        assert result == "674"
        assert isinstance(result, str)

    def test_get_ticket_valid_success(
        self,
        mocker: MockerFixture,
        api_manager: ConnectWiseManager,
    ) -> None:
        # Arrange
        mock_request(
            mocker,
            method="GET",
            request_string="ticket_valid",
            response_code=STATUS_CODES.get("SUCCESS"),
        )

        # Act
        result = api_manager.get_ticket(ticket_id="674")

        # Assert
        assert result["id"] == 674
        assert isinstance(result, dict)
