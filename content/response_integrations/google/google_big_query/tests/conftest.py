# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import annotations

import importlib
import pkgutil
import sys
from unittest.mock import MagicMock, Mock

import pytest
import soar_sdk

sdk_dir = soar_sdk.__path__[0]
if sdk_dir not in sys.path:
    sys.path.insert(0, sdk_dir)
original_stdout = sys.stdout
for _, name, _ in pkgutil.iter_modules(soar_sdk.__path__):
    try:
        flat_mod = importlib.import_module(name)
        sys.modules[f"soar_sdk.{name}"] = flat_mod
        setattr(soar_sdk, name, flat_mod)
    except Exception:
        pass
sys.stdout = original_stdout

from TIPCommon.types import SingleJson  # noqa: E402

from google_big_query.core import data_models  # noqa: E402
from google_big_query.core.GoogleBigQueryManager import (  # noqa: E402
    GoogleBigQueryApiManager,
)
from google_big_query.core.GoogleBigQueryUtils import (  # noqa: E402
    ExtractConfigurationParameters,
)


class BigQueryApiClientMock:
    """Mock BigQuery client for unit tests."""

    @staticmethod
    def list_datasets(*_: object, **__: object) -> list[Mock]:
        return [Mock(), Mock()]

    @staticmethod
    def query(*_: object, **__: object) -> list[SingleJson]:
        return [{"test": "asd"}, {"test": "sdf"}]


class Mockplify:
    """Mock SOAR SDK handle for unit tests."""

    LOGGER = MagicMock()

    @staticmethod
    def get_configuration(_: object) -> SingleJson:
        return {
            "Account Type": "account_type",
            "Project ID": "project_id",
            "Private Key ID": "private_key_id",
            "Private Key": "private_key",
            "Client Email": "client_email",
            "Client ID": "client_id",
            "Auth URI": "auth_uri",
            "Token URI": "token_uri",
            "Client X509 URL": "auth_provider_x509_url",
            "Auth Provider X509 URL": "auth_provider_x509_url",
            "Service Account Json File Content": '{"service": "account"}',
            "Workload Identity Email": "workload@identity.email",
            "Quota Project ID": "quota_project_id",
            "Verify SSL": False,
        }


@pytest.fixture
def mockplify() -> Mockplify:
    """Return mock SOAR SDK object."""
    return Mockplify()


@pytest.fixture
def conf_param_extractor() -> ExtractConfigurationParameters:
    """Return configuration parameter extractor fixture."""
    return ExtractConfigurationParameters(Mockplify())


@pytest.fixture
def google_sa() -> data_models.GoogleServiceAccount:
    """Return populated GoogleServiceAccount fixture."""
    return data_models.GoogleServiceAccount(
        account_type="account_type",
        project_id="project_id",
        private_key_id="private_key_id",
        private_key="private_key",
        client_email="client_email",
        client_id="client_id",
        auth_uri="auth_uri",
        token_uri="token_uri",
        client_x509_cert_url="client_x509_cert_url",
        auth_provider_x509_url="auth_provider_x509_url",
    )


@pytest.fixture
def empty_google_sa() -> data_models.GoogleServiceAccount:
    """Return empty GoogleServiceAccount fixture."""
    return data_models.GoogleServiceAccount(
        account_type=None,
        project_id=None,
        private_key_id=None,
        private_key=None,
        client_email=None,
        client_id=None,
        auth_uri=None,
        token_uri=None,
        client_x509_cert_url=None,
        auth_provider_x509_url=None,
    )


@pytest.fixture
def manager() -> GoogleBigQueryApiManager:
    """Return GoogleBigQueryApiManager backed by mock client."""
    return GoogleBigQueryApiManager("project_id", BigQueryApiClientMock())
