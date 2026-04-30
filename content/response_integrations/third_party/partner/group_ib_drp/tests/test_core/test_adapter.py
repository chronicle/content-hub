"""Unit tests for ``core.adapter.create_drp_poller``.

The adapter is a four-line factory but it's the boundary between the
integration's configuration and ciaops's ``DRPPoller``. Breakage here
silently disables every action and connector at runtime.
"""

from __future__ import annotations

import pathlib
import sys
import sysconfig

_SITE_PACKAGES = pathlib.Path(sysconfig.get_paths()["purelib"])
_SOAR_SDK_DIR = _SITE_PACKAGES / "soar_sdk"
if _SOAR_SDK_DIR.is_dir() and str(_SOAR_SDK_DIR) not in sys.path:
    sys.path.insert(0, str(_SOAR_SDK_DIR))

from unittest.mock import MagicMock, patch  # noqa: E402

from group_ib_drp.core.adapter import create_drp_poller  # noqa: E402
from group_ib_drp.core.mapping import mapping_config  # noqa: E402


class TestCreateDRPPoller:
    """Validate that the adapter wires the right credentials, toggles SSL
    verification, and applies every collection's key mapping before
    returning the poller."""

    def test_returns_drp_poller_constructed_with_user_credentials(self):
        with patch("group_ib_drp.core.adapter.DRPPoller") as poller_cls:
            poller_cls.return_value = MagicMock(name="DRPPoller_instance")
            poller = create_drp_poller(
                username="u",
                api_key="k",
                api_url="https://drp.example.com/api/",
                verify_ssl=True,
            )
        poller_cls.assert_called_once_with(
            username="u",
            api_key="k",
            api_url="https://drp.example.com/api/",
        )
        assert poller is poller_cls.return_value

    def test_propagates_verify_ssl_flag_to_poller(self):
        with patch("group_ib_drp.core.adapter.DRPPoller") as poller_cls:
            instance = MagicMock(name="DRPPoller_instance")
            poller_cls.return_value = instance
            create_drp_poller(
                username="u",
                api_key="k",
                api_url="https://drp.example.com/api/",
                verify_ssl=False,
            )
        instance.set_verify.assert_called_once_with(False)

    def test_applies_every_mapping_collection_via_set_keys(self):
        with patch("group_ib_drp.core.adapter.DRPPoller") as poller_cls:
            instance = MagicMock(name="DRPPoller_instance")
            poller_cls.return_value = instance
            create_drp_poller(
                username="u",
                api_key="k",
                api_url="https://drp.example.com/api/",
            )
        actual_collections = {call.kwargs["collection_name"] for call in instance.set_keys.call_args_list}
        assert actual_collections == set(mapping_config.keys())
        for call in instance.set_keys.call_args_list:
            collection = call.kwargs["collection_name"]
            assert call.kwargs["keys"] == mapping_config[collection]

    def test_default_verify_ssl_is_true(self):
        with patch("group_ib_drp.core.adapter.DRPPoller") as poller_cls:
            instance = MagicMock(name="DRPPoller_instance")
            poller_cls.return_value = instance
            create_drp_poller(
                username="u",
                api_key="k",
                api_url="https://drp.example.com/api/",
            )
        instance.set_verify.assert_called_once_with(True)
