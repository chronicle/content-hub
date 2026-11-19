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

import google.auth.transport.requests
import pytest
import requests

import pub_sub.core.PubSubAuthManager
from pub_sub.tests.core.session import ApiSession
from pub_sub.tests.core.product import Product
from integration_testing.common import use_live_api


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
            google.auth.transport.requests.AuthorizedSession,
            "__new__",
            __get_client_session
        )
        monkeypatch.setattr(
            pub_sub.Managers.PubSubAuthManager,
            "AuthorizedSession",
            __get_client_session
        )

    yield session

@pytest.fixture(name='sdk_session', autouse=True)
def sdk_session_fixture(script_session):
    return script_session
