"""Unit tests for the ``Ping`` action.

Ping is the simplest action — it just runs a low-cost GET against
``violation/list`` to confirm credentials are valid. We patch the
module's ``SiemplifyAction`` and ``GIBConnector`` to inject a
:class:`FakeDRPPoller` so the test can assert on the exact request
issued and on the action's final state without touching the real DRP
API.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED

from ..common import ACTIONS_PATH, load_script


@pytest.fixture
def ping_module():
    """Load ``actions/Ping.py`` as a regular Python module.

    The DRP file lives at ``actions/Ping.py`` (no spaces in this one but
    ``load_script`` handles both, and using it here keeps the fixture
    consistent with the other actions whose names do contain spaces).
    """
    return load_script(ACTIONS_PATH, "Ping.py", "Ping")


class TestPing:
    """Connectivity-check action; both the success and failure paths must
    deterministically report through ``siemplify.end``."""

    def test_ping_success(self, ping_module, action_siemplify_factory, fake_poller):
        """A successful GET against ``violation/list`` ends with ``COMPLETED``."""

        siemplify = action_siemplify_factory()
        with (
            patch.object(ping_module, "SiemplifyAction", return_value=siemplify),
            patch.object(ping_module, "GIBConnector") as gib_cls,
        ):
            gib_cls.return_value.init_action_poller.return_value = fake_poller
            ping_module.main()

        send_calls = fake_poller.calls_to("send_request")
        assert len(send_calls) == 1
        assert send_calls[0].args == ("violation/list",)
        assert send_calls[0].kwargs["params"] == {"q": None}

        assert len(siemplify._end_calls) == 1
        end = siemplify._end_calls[0]
        assert "Successfully connected" in end["message"]
        assert end["result_value"] is True
        assert end["status"] == EXECUTION_STATE_COMPLETED

    def test_ping_failure(self, ping_module, action_siemplify_factory, fake_poller):
        """An exception bubbling from the API must surface as ``FAILED``."""

        siemplify = action_siemplify_factory()
        with (
            patch.object(ping_module, "SiemplifyAction", return_value=siemplify),
            patch.object(ping_module, "GIBConnector") as gib_cls,
        ):
            gib_cls.return_value.init_action_poller.return_value = fake_poller
            with fake_poller.fail_requests("Connection refused"):
                ping_module.main()

        assert len(fake_poller.calls_to("send_request")) == 1
        siemplify.LOGGER.exception.assert_called()

        end = siemplify._end_calls[0]
        assert "Failed to connect" in end["message"]
        assert "Connection refused" in end["message"]
        assert end["result_value"] is False
        assert end["status"] == EXECUTION_STATE_FAILED

    def test_ping_sets_script_name(self, ping_module, action_siemplify_factory, fake_poller):
        """The script name must match ``Config.GC_PING`` so SOAR's run logs
        and metrics tag this run as the Ping action."""
        siemplify = action_siemplify_factory()
        with (
            patch.object(ping_module, "SiemplifyAction", return_value=siemplify),
            patch.object(ping_module, "GIBConnector") as gib_cls,
        ):
            gib_cls.return_value.init_action_poller.return_value = fake_poller
            ping_module.main()
        assert siemplify.script_name == "Ping"
