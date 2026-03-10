from unittest.mock import MagicMock, patch
import requests
from integration_testing.set_meta import set_metadata
from actions.RemoveIpFromAllowList import main
from core.SignalSciencesManager import SignalSciencesManager
from TIPCommon.base.action.data_models import ExecutionState
from common import CONFIG_PATH


@set_metadata(
    parameters={
        "Site Name": "test-site",
        "IP Address": "1.2.3.4",
    },
    integration_config_file_path=CONFIG_PATH,
)
@patch.object(SignalSciencesManager, "get_allowlists")
@patch.object(SignalSciencesManager, "remove_ip_from_allowlist")
def test_remove_ip_from_allow_list_success(
    mock_remove_ip, mock_get_allow, script_session, action_output
):
    mock_get_allow.return_value = [{
        "id": "12345",
        "source": "1.2.3.4",
        "note": "Test Note",
        "createdBy": "admin@example.com",
        "created": "2024-01-01T00:00:00Z"
    }]

    main()

    mock_remove_ip.assert_called_once_with(
        site_name="test-site",
        item_id="12345"
    )

    assert (
        "Successfully removed the following IPs from the Allow List for "
        "site test-site in Signal Sciences:\n1.2.3.4"
    ) in action_output.results.output_message
    assert action_output.results.is_success is True
    assert action_output.results.execution_state == ExecutionState.COMPLETED


@set_metadata(
    parameters={
        "Site Name": "test-site",
        "IP Address": "1.2.3.4",
    },
    integration_config_file_path=CONFIG_PATH,
)
@patch.object(SignalSciencesManager, "get_allowlists")
@patch.object(SignalSciencesManager, "remove_ip_from_allowlist")
def test_remove_ip_from_allow_list_not_found(
    mock_remove_ip, mock_get_allow, script_session, action_output
):
    mock_get_allow.return_value = [] # IP not in allowlist

    main()

    # Verify no remove call was made
    mock_remove_ip.assert_not_called()

    assert (
        "Successfully removed the following IPs from the Allow List for "
        "site test-site in Signal Sciences:\n1.2.3.4"
    ) in action_output.results.output_message
    assert action_output.results.is_success is True
    assert action_output.results.execution_state == ExecutionState.COMPLETED


@set_metadata(
    parameters={
        "Site Name": "test-site",
        "IP Address": "1.2.3.4",
    },
    integration_config_file_path=CONFIG_PATH,
)
@patch.object(SignalSciencesManager, "get_allowlists")
@patch.object(SignalSciencesManager, "remove_ip_from_allowlist")
def test_remove_ip_from_allow_list_duplicates(
    mock_remove_ip, mock_get_allow, script_session, action_output
):
    mock_get_allow.return_value = [
        {"id": "id1", "source": "1.2.3.4"},
        {"id": "id2", "source": "1.2.3.4"},
    ]

    main()

    assert mock_remove_ip.call_count == 2
    assert (
        "Successfully removed the following IPs from the Allow List for "
        "site test-site in Signal Sciences:\n1.2.3.4"
    ) in action_output.results.output_message
    assert action_output.results.is_success is True

@set_metadata(
    parameters={
        "Site Name": "test-site",
        "IP Address": "",
    },
    integration_config_file_path=CONFIG_PATH,
)
@patch.object(SignalSciencesManager, "get_allowlists")
def test_remove_ip_from_allow_list_no_ips(
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
def test_remove_ip_from_allow_list_site_not_found(
    mock_get_allow, script_session, action_output
):
    # Mocking the error response for Site not found
    error_response = MagicMock(spec=requests.Response)
    error_response.json.return_value = {"message": "Site not found"}
    http_error = requests.exceptions.HTTPError("400 Client Error", response=error_response)
    mock_get_allow.side_effect = http_error

    main()

    assert 'Error executing action: "Remove IP from Allow List". Reason: Site non-existent-site not found.' in action_output.results.output_message
    assert action_output.results.is_success is False
    assert action_output.results.execution_state == ExecutionState.FAILED


@set_metadata(
    parameters={
        "Site Name": "test-site",
        "IP Address": "1.2.3.4, 5.6.7.8",
    },
    integration_config_file_path=CONFIG_PATH,
)
@patch.object(SignalSciencesManager, "get_allowlists")
@patch.object(SignalSciencesManager, "remove_ip_from_allowlist")
def test_remove_ip_from_allow_list_partial_success(
    mock_remove_ip, mock_get_allow, script_session, action_output
):
    mock_get_allow.return_value = [
        {"id": "id1", "source": "1.2.3.4"},
        {"id": "id2", "source": "5.6.7.8"},
    ]
    
    def remove_ip_side_effect(site_name, item_id):
        if item_id == "id1":
            return
        raise Exception("API Error for 5.6.7.8")
        
    mock_remove_ip.side_effect = remove_ip_side_effect

    main()

    assert "Successfully removed the following IPs" in action_output.results.output_message
    assert "Failed to remove the following IPs" in action_output.results.output_message
    assert action_output.results.is_success is False
    assert action_output.results.execution_state == ExecutionState.COMPLETED


@set_metadata(
    parameters={
        "Site Name": "test-site",
        "IP Address": "1.2.3.4",
    },
    integration_config_file_path=CONFIG_PATH,
)
@patch.object(SignalSciencesManager, "get_allowlists")
@patch.object(SignalSciencesManager, "remove_ip_from_allowlist")
def test_remove_ip_from_allow_list_full_failure(
    mock_remove_ip, mock_get_allow, script_session, action_output
):
    mock_get_allow.return_value = [{"id": "id1", "source": "1.2.3.4"}]
    mock_remove_ip.side_effect = Exception("API Error")

    main()

    assert 'Error executing action: "Remove IP from Allow List". Reason: Failed to remove' in action_output.results.output_message
    assert action_output.results.is_success is False
    assert action_output.results.execution_state == ExecutionState.FAILED
