from __future__ import annotations
from tanium.core.TaniumManager import TaniumManager
from tanium.core.constants import INTEGRATION_VERSION


def test_tanium_manager_headers(mocker):
    mocker.patch.object(TaniumManager, "test_connectivity")

    manager = TaniumManager(
        api_token="dummy_token",
        api_root="https://dummy_url",
        verify_ssl=False,
        force_check_connectivity=False,
    )

    assert "x-tanium-integration" in manager.session.headers
    assert (
        manager.session.headers["x-tanium-integration"]
        == f"googlesecops-taniumrest-{INTEGRATION_VERSION}"
    )
