from __future__ import annotations
pytest_plugins = ("integration_testing.conftest",)
import sys
import os
import pkgutil
import importlib
import soar_sdk
sdk_dir = soar_sdk.__path__[0]
if sdk_dir not in sys.path:
    sys.path.insert(0, sdk_dir)
original_stdout = sys.stdout
for _, name, _ in pkgutil.iter_modules(soar_sdk.__path__):
    try:
        flat_mod = importlib.import_module(name)
        sys.modules[f'soar_sdk.{name}'] = flat_mod
        setattr(soar_sdk, name, flat_mod)
    except Exception:
        pass
sys.stdout = original_stdout

import google.auth
import google.auth.transport.requests
import google.oauth2.credentials
from integration_testing.common import use_live_api
import pytest
import requests

from pub_sub.core import PubSubAuthManager
from pub_sub.tests.core.product import Product
from pub_sub.tests.core.session import ApiSession


@pytest.fixture
def pub_sub() -> Product:
    return Product()


# pylint: disable=redefined-outer-name
@pytest.fixture(autouse=True)
def gcloud_pubsub_script_session(
        monkeypatch: pytest.MonkeyPatch,
        pub_sub: Product,
) -> ApiSession:
    """Mock Gcloud Pub/Sub session to view request history."""
    session: ApiSession = ApiSession(pub_sub)
    def __get_client_session(*_, **kwargs) -> ApiSession:
        if "credentials" in kwargs:
            session.credentials = kwargs["credentials"]
        return session

    if not use_live_api():
        monkeypatch.setattr(requests, "Session", lambda: session)
        monkeypatch.setattr(
            google.auth,
            "default",
            lambda *_, **__: (
                google.oauth2.credentials.Credentials(
                    token=None,
                    refresh_token="mock-refresh-token",
                    token_uri="https://oauth2.googleapis.com/token",
                    client_id="mock-client-id",
                    client_secret="mock-client-secret",
                ),
                "test-project",
            ),
        )
        monkeypatch.setattr(
            PubSubAuthManager,
            "get_workload_sa_email",
            lambda default_sa="": default_sa or "default@domain.com",
        )
        monkeypatch.setattr(
            google.auth.transport.requests.AuthorizedSession,
            "__new__",
            __get_client_session,
        )
        monkeypatch.setattr(
            PubSubAuthManager,
            "AuthorizedSession",
            __get_client_session,
        )

    yield session
