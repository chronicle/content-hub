from typing import Any
from zscaler.actions import Ping


def test_ping_isolated(
    script_session: Any,
    mock_siemplify: Any,
    action_output: Any,
) -> None:
    _ = script_session
    _ = mock_siemplify

    Ping.main()

    assert action_output.is_success is True
    assert "Connection Established" in action_output.output_message
