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

import pathlib

import google.auth.transport.requests
import pytest
import requests

from TIPCommon.types import SingleJson

import vertex_ai.core.VertexAIAuthManager
from vertex_ai.core.VertexAIAuthManager import (
    AuthManager,
    AuthManagerParams,
)
from vertex_ai.core.VertexAIApiManager import ApiManager
from vertex_ai.tests.core.session import ApiSession
from integration_testing.common import get_def_file_content, use_live_api
from integration_testing.logger import Logger

CONFIG_PATH: pathlib.Path = pathlib.Path(__file__).parent / "config.json"
CONFIG: SingleJson = get_def_file_content(CONFIG_PATH)


@pytest.fixture(autouse=True)
def vertexai_script_session(
    mocker,
    monkeypatch: pytest.MonkeyPatch,
) -> ApiSession:
    """Mock Vertex AI session and get back an object to view request history"""
    session = ApiSession()
    # pylint: disable=protected-access
    session._auth_request = session.credentials = mocker.Mock()
    if not use_live_api():
        monkeypatch.setattr(requests, "Session", lambda: session)
        monkeypatch.setattr(
            google.auth.transport.requests.AuthorizedSession,
            "__new__",
            lambda *args, **kwargs: session
        )
        monkeypatch.setattr(
            vertex_ai.Managers.VertexAIAuthManager,
            "AuthorizedSession",
            lambda *args, **kwargs: session
        )

    yield session


# pylint: disable=redefined-outer-name
@pytest.fixture
def vertexai_manager() -> ApiManager:
    """Vertex AI ApiManager."""
    api_root = CONFIG["API Root"]
    verify_ssl: bool = CONFIG["Verify SSL"]
    location_id = CONFIG["Location ID"]
    workload_identity_email = CONFIG["Workload Identity Email"]
    service_account_json = CONFIG["Service Account Json File Content"]
    project_id = CONFIG["Project ID"]
    auth_params = AuthManagerParams(
        verify_ssl=verify_ssl,
        project_id=project_id,
        service_account_json=service_account_json,
        workload_identity_email=workload_identity_email,
    )
    auth_manager = AuthManager(auth_params)

    return ApiManager(
        api_root=api_root,
        session=auth_manager.prepare_session(),
        location_id=location_id,
        project_id=auth_manager.project_id,
        logger=Logger()
    )

@pytest.fixture(name='sdk_session', autouse=True)
def sdk_session_fixture(script_session):
    return script_session
