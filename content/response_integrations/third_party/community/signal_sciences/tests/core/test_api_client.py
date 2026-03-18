from __future__ import annotations

import pytest

from signal_sciences.core.api.api_client import SignalSciencesApiClient, ApiParameters
from signal_sciences.core.auth import AuthenticatedSession, SessionAuthenticationParameters
from signal_sciences.tests.core.product import SignalSciencesProduct
from signal_sciences.tests.core.session import SignalSciencesSession
from unittest.mock import MagicMock


class TestSignalSciencesApiClient:
    def test_list_sites(
        self,
        script_session: SignalSciencesSession,
        signal_sciences: SignalSciencesProduct,
    ) -> None:
        # Arrange
        auth_session = AuthenticatedSession()
        auth_session.authenticate_session(SessionAuthenticationParameters("e", "t", True))
        config = ApiParameters(api_root="https://dashboard.signalsciences.net", corp_name="corp")
        logger = MagicMock()

        client = SignalSciencesApiClient(auth_session.session, config, logger)
        signal_sciences.add_site({"name": "site1"})

        # Act
        sites = client.list_sites()

        # Assert
        assert len(sites) == 1
        assert sites[0]["name"] == "site1"
        
        assert len(script_session.request_history) == 1
        request = script_session.request_history[0].request
        assert request.url.path == "/api/v0/corps/corp/sites"

    def test_get_allowlist(
        self,
        script_session: SignalSciencesSession,
        signal_sciences: SignalSciencesProduct,
    ) -> None:
        auth_session = AuthenticatedSession()
        auth_session.authenticate_session(SessionAuthenticationParameters("e", "t", True))
        config = ApiParameters(api_root="https://api", corp_name="corp")
        client = SignalSciencesApiClient(auth_session.session, config, MagicMock())
        signal_sciences.add_whitelist_item("site1", {"source": "1.1.1.1"})

        items = client.get_allowlist("site1")

        assert len(items) == 1
        assert items[0]["source"] == "1.1.1.1"
        assert script_session.request_history[0].request.url.path == "/api/v0/corps/corp/sites/site1/whitelist"

    def test_add_allowlist_item(
        self,
        script_session: SignalSciencesSession,
        signal_sciences: SignalSciencesProduct,
    ) -> None:
        auth_session = AuthenticatedSession()
        auth_session.authenticate_session(SessionAuthenticationParameters("e", "t", True))
        config = ApiParameters(api_root="https://api", corp_name="corp")
        client = SignalSciencesApiClient(auth_session.session, config, MagicMock())
        payload = {"source": "1.1.1.1"}

        client.add_allowlist_item("site1", payload)

        assert script_session.request_history[0].request.method.value == "PUT"
        assert script_session.request_history[0].request.url.path == "/api/v0/corps/corp/sites/site1/whitelist"

    def test_delete_allowlist_item(
        self,
        script_session: SignalSciencesSession,
        signal_sciences: SignalSciencesProduct,
    ) -> None:
        auth_session = AuthenticatedSession()
        auth_session.authenticate_session(SessionAuthenticationParameters("e", "t", True))
        config = ApiParameters(api_root="https://api", corp_name="corp")
        client = SignalSciencesApiClient(auth_session.session, config, MagicMock())
        signal_sciences.add_whitelist_item("site1", {"source": "1.1.1.1", "id": "wl_1"})

        client.delete_allowlist_item("site1", "wl_1")

        assert script_session.request_history[0].request.method.value == "DELETE"
        assert script_session.request_history[0].request.url.path == "/api/v0/corps/corp/sites/site1/whitelist/wl_1"

    def test_get_blocklist(
        self,
        script_session: SignalSciencesSession,
        signal_sciences: SignalSciencesProduct,
    ) -> None:
        auth_session = AuthenticatedSession()
        auth_session.authenticate_session(SessionAuthenticationParameters("e", "t", True))
        config = ApiParameters(api_root="https://api", corp_name="corp")
        client = SignalSciencesApiClient(auth_session.session, config, MagicMock())
        signal_sciences.add_blacklist_item("site1", {"source": "2.2.2.2"})

        items = client.get_blocklist("site1")

        assert len(items) == 1
        assert items[0]["source"] == "2.2.2.2"
        assert script_session.request_history[0].request.url.path == "/api/v0/corps/corp/sites/site1/blacklist"

    def test_add_blocklist_item(
        self,
        script_session: SignalSciencesSession,
        signal_sciences: SignalSciencesProduct,
    ) -> None:
        auth_session = AuthenticatedSession()
        auth_session.authenticate_session(SessionAuthenticationParameters("e", "t", True))
        config = ApiParameters(api_root="https://api", corp_name="corp")
        client = SignalSciencesApiClient(auth_session.session, config, MagicMock())
        payload = {"source": "2.2.2.2"}

        client.add_blocklist_item("site1", payload)

        assert script_session.request_history[0].request.method.value == "PUT"
        assert script_session.request_history[0].request.url.path == "/api/v0/corps/corp/sites/site1/blacklist"

    def test_delete_blocklist_item(
        self,
        script_session: SignalSciencesSession,
        signal_sciences: SignalSciencesProduct,
    ) -> None:
        auth_session = AuthenticatedSession()
        auth_session.authenticate_session(SessionAuthenticationParameters("e", "t", True))
        config = ApiParameters(api_root="https://api", corp_name="corp")
        client = SignalSciencesApiClient(auth_session.session, config, MagicMock())
        signal_sciences.add_blacklist_item("site1", {"source": "2.2.2.2", "id": "bl_1"})

        client.delete_blocklist_item("site1", "bl_1")

        assert script_session.request_history[0].request.method.value == "DELETE"
        assert script_session.request_history[0].request.url.path == "/api/v0/corps/corp/sites/site1/blacklist/bl_1"
