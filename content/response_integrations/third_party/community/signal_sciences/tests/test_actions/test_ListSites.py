from unittest.mock import MagicMock, patch

from integration_testing.set_meta import set_metadata
from actions.ListSites import main
from core.SignalSciencesManager import SignalSciencesManager
from TIPCommon.base.action.data_models import ExecutionState
from common import CONFIG_PATH, SITES_DATA


@set_metadata(
    parameters={"Max Sites To Return": 50},
    integration_config_file_path=CONFIG_PATH,
)
@patch.object(SignalSciencesManager, "get_sites")
def test_list_sites_success(mock_get_sites, script_session, action_output):
    mock_get_sites.return_value = SITES_DATA

    main()

    mock_get_sites.assert_called_once_with(max_records=50)
    assert (
        "Successfully fetched information about the following sites in Signal "
        "Sciences:\nsite1"
    ) in action_output.results.output_message
    assert action_output.results.is_success is True
    assert action_output.results.execution_state == ExecutionState.COMPLETED


@set_metadata(
    parameters={"Max Sites To Return": 0},
    integration_config_file_path=CONFIG_PATH,
)
@patch.object(SignalSciencesManager, "get_sites")
def test_list_sites_unlimited(mock_get_sites, script_session, action_output):
    mock_get_sites.return_value = [
        {"name": f"site{i}", "displayName": f"Site {i}", "created": "2024", "agentLevel": "log"}
        for i in range(15)
    ]

    main()

    mock_get_sites.assert_called_once_with(max_records=0)
    assert action_output.results.execution_state == ExecutionState.COMPLETED


@set_metadata(
    parameters={"Max Sites To Return": None},
    integration_config_file_path=CONFIG_PATH,
)
@patch.object(SignalSciencesManager, "get_sites")
def test_list_sites_empty_param(mock_get_sites, script_session, action_output):
    mock_get_sites.return_value = [{"name": "site1"}]

    main()

    # Should be 0 since None is converted to 0 in the script
    mock_get_sites.assert_called_once_with(max_records=0)
    assert action_output.results.execution_state == ExecutionState.COMPLETED
