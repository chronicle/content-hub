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
from typing import TYPE_CHECKING

import google.auth
import google.auth.transport.requests
import google.oauth2.credentials
from integration_testing.common import get_def_file_content, use_live_api
from integration_testing.logger import Logger
import pytest
import requests

from web_risk.core import WebRiskAuthManager
from web_risk.core.WebRiskApiManager import ApiManager
from web_risk.core.WebRiskAuthManager import (
    AuthManager,
    AuthManagerParams,
)
from web_risk.tests.core.product import Product
from web_risk.tests.core.session import ApiSession

if TYPE_CHECKING:
    from collections.abc import Iterator

    from TIPCommon.types import SingleJson

CONFIG_PATH: pathlib.Path = pathlib.Path(__file__).parent / "config.json"
CONFIG: SingleJson = get_def_file_content(CONFIG_PATH)


# pylint: disable=redefined-outer-name
@pytest.fixture
def product() -> Product:
    return Product()


@pytest.fixture(autouse=True)
def script_session(
    monkeypatch: pytest.MonkeyPatch,
    product: Product,
) -> Iterator[ApiSession]:
    """Mock Gcloud API session and get back an object to view request history."""
    session = ApiSession(product)
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
            WebRiskAuthManager,
            "get_workload_sa_email",
            lambda default_sa="": default_sa or "default@domain.com",
        )
        monkeypatch.setattr(
            google.auth.transport.requests.AuthorizedSession,
            "__new__",
            lambda *_args, **_kwargs: session,
        )
        monkeypatch.setattr(
            WebRiskAuthManager,
            "AuthorizedSession",
            lambda *_args, **_kwargs: session,
        )
    yield session


@pytest.fixture
def gcloud_api_manager() -> ApiManager:
    """GoogleGmailApiManager manager."""
    api_root = CONFIG["API Root"]
    verify_ssl: bool = CONFIG["Verify SSL"]
    workload_identity_email = CONFIG["Workload Identity Email"]
    service_account_json = CONFIG["Service Account Json File Content"]
    project_id = CONFIG["Project ID"]
    quota_project_id = CONFIG["Quota Project ID"]
    auth_manager = AuthManager(
        AuthManagerParams(
            verify_ssl=verify_ssl,
            project_id=project_id,
            quota_project_id=quota_project_id,
            service_account_json=service_account_json,
            workload_identity_email=workload_identity_email,
        )
    )

    return ApiManager(
        api_root=api_root,
        session=auth_manager.prepare_session(),
        project_id=auth_manager.project_id,
        logger=Logger(),
    )
