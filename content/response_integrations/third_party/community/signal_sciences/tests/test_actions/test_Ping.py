from unittest.mock import MagicMock, patch

from integration_testing.set_meta import set_metadata
from actions.Ping import main
from core.SignalSciencesManager import SignalSciencesManager
from TIPCommon.base.action.data_models import ExecutionState
from common import CONFIG_PATH


@set_metadata(
    parameters={},
    integration_config_file_path=CONFIG_PATH,
)
@patch.object(SignalSciencesManager, "test_connectivity")
def test_ping_success(mock_test_conn, script_session, action_output):
    mock_test_conn.return_value = True

    main()

    mock_test_conn.assert_called_once()
    assert (
        "Successfully connected to the Signal Sciences server with the "
        "provided connection parameters!"
    ) in action_output.results.output_message
    assert action_output.results.is_success is True
    assert action_output.results.execution_state == ExecutionState.COMPLETED
