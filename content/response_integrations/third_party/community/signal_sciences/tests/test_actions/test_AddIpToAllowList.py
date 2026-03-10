from unittest.mock import MagicMock, patch
import requests
from integration_testing.set_meta import set_metadata
from actions.AddIpToAllowList import main
from core.SignalSciencesManager import SignalSciencesManager
from TIPCommon.base.action.data_models import ExecutionState
from common import CONFIG_PATH, IP_RESPONSES_DATA


@set_metadata(
    parameters={
        "Site Name": "test-site",
        "IP Address": "1.2.3.4",
        "Note": "Test Note",
    },
    integration_config_file_path=CONFIG_PATH,
)
@patch.object(SignalSciencesManager, "get_allowlists")
@patch.object(SignalSciencesManager, "add_ip_to_allowlist")
def test_add_ip_to_allow_list_success(
    mock_add_ip, mock_get_allow, script_session, action_output
):
    mock_get_allow.return_value = []
    mock_add_ip.return_value = IP_RESPONSES_DATA["allow_list_response"][0]["EntityResult"]

    main()

    mock_add_ip.assert_called_once_with(
        site_name="test-site",
        ip_address="1.2.3.4",
        note="Test Note"
    )

    assert (
        "Successfully added the following IPs to the Allow List for "
        "site test-site in Signal Sciences:\n1.2.3.4"
    ) in action_output.results.output_message
    assert action_output.results.is_success is True
    assert action_output.results.execution_state == ExecutionState.COMPLETED
    assert action_output.results.json_output == [
        {
            "Entity": "1.2.3.4",
            "EntityResult": {
                "id": "558cde293dfaa4a829000009",
                "source": "1.1.1.1", # Note: Spec had 1.1.1.1, test had 1.2.3.4, I'll keep the mock's 1.1.1.1
                "note": "Example Note",
                "createdBy": "user@example.com",
                "created": "2014-12-11T22:51:56-08:00",
                "expires": ""
            }
        }
    ]


@set_metadata(
    parameters={
        "Site Name": "test-site",
        "IP Address": "1.2.3.4",
        "Note": "Test Note",
    },
    integration_config_file_path=CONFIG_PATH,
)
@patch.object(SignalSciencesManager, "get_allowlists")
@patch.object(SignalSciencesManager, "add_ip_to_allowlist")
def test_add_ip_to_allow_list_failure(
    mock_add_ip, mock_get_allow, script_session, action_output
):
    mock_get_allow.return_value = []
    mock_add_ip.side_effect = Exception("API Error")

    main()

    mock_add_ip.assert_called_once_with(
        site_name="test-site",
        ip_address="1.2.3.4",
        note="Test Note"
    )
    assert (
        'Error executing action: "Add IP to Allow List". Reason: Failed to add '
        'the following IPs to the Allow List for site test-site in Signal Sciences:\n1.2.3.4'
    ) in action_output.results.output_message
    assert action_output.results.is_success is False
    assert action_output.results.execution_state == ExecutionState.COMPLETED


@set_metadata(
    parameters={
        "Site Name": "test-site",
        "IP Address": "1.2.3.4",
        "Note": "Test Note",
    },
    integration_config_file_path=CONFIG_PATH,
)
@patch.object(SignalSciencesManager, "get_allowlists")
@patch.object(SignalSciencesManager, "add_ip_to_allowlist")
def test_add_ip_to_allow_list_already_exists(
    mock_add_ip, mock_get_allow, script_session, action_output
):
    mock_get_allow.return_value = [{
        "id": "existing-123",
        "source": "1.2.3.4",
        "note": "Existing Note",
        "createdBy": "other@example.com",
        "created": "2023-12-31T00:00:00Z"
    }]

    main()

    # Verify no addition call was made
    mock_add_ip.assert_not_called()

    assert (
        "Successfully added the following IPs to the Allow List for "
        "site test-site in Signal Sciences:\n1.2.3.4"
    ) in action_output.results.output_message
    assert action_output.results.is_success is True
    assert action_output.results.execution_state == ExecutionState.COMPLETED
    assert action_output.results.json_output == [
        {
            "Entity": "1.2.3.4",
            "EntityResult": {
                "id": "existing-123",
                "source": "1.2.3.4",
                "note": "Existing Note",
                "createdBy": "other@example.com",
                "created": "2023-12-31T00:00:00Z",
                "expires": None
            }
        }
    ]

@set_metadata(
    parameters={
        "Site Name": "test-site",
        "IP Address": "",
    },
    integration_config_file_path=CONFIG_PATH,
)
@patch.object(SignalSciencesManager, "get_allowlists")
def test_add_ip_to_allow_list_no_ips(
    mock_get_allow, script_session, action_output
):
    main()

    assert (
        "No IP addresses were provided as parameters or found as entities."
    ) in action_output.results.output_message
    assert action_output.results.is_success is False
    assert action_output.results.execution_state == ExecutionState.COMPLETED

@set_metadata(
    parameters={
        "Site Name": "non-existent-site",
        "IP Address": "1.2.3.4",
    },
    integration_config_file_path=CONFIG_PATH,
)
@patch.object(SignalSciencesManager, "get_allowlists")
def test_add_ip_to_allow_list_site_not_found(
    mock_get_allow, script_session, action_output
):
    # Mocking the error response for Site not found
    error_response = MagicMock(spec=requests.Response)
    error_response.json.return_value = {"message": "Site not found"}
    http_error = requests.exceptions.HTTPError("400 Client Error", response=error_response)
    mock_get_allow.side_effect = http_error

    main()

    assert 'Error executing action: "Add IP to Allow List". Reason: Site non-existent-site not found.' in action_output.results.output_message
    assert action_output.results.is_success is False
    assert action_output.results.execution_state == ExecutionState.FAILED


@set_metadata(
    parameters={
        "Site Name": "test-site",
        "IP Address": "1.2.3.4, 5.6.7.8",
        "Note": "Test Note",
    },
    integration_config_file_path=CONFIG_PATH,
)
@patch.object(SignalSciencesManager, "get_allowlists")
@patch.object(SignalSciencesManager, "add_ip_to_allowlist")
def test_add_ip_to_allow_list_partial_success(
    mock_add_ip, mock_get_allow, script_session, action_output
):
    mock_get_allow.return_value = []
    
    def add_ip_side_effect(site_name, ip_address, note):
        if ip_address == "1.2.3.4":
            return {
                "id": "12345",
                "source": "1.2.3.4",
                "note": "Test Note",
                "createdBy": "admin@example.com",
                "created": "2024-01-01T00:00:00Z"
            }
        raise Exception("API Error for 5.6.7.8")
        
    mock_add_ip.side_effect = add_ip_side_effect

    main()

    assert "Successfully added the following IPs" in action_output.results.output_message
    assert "Failed to add the following IPs" in action_output.results.output_message
    assert action_output.results.is_success is False
    assert action_output.results.execution_state == ExecutionState.COMPLETED
