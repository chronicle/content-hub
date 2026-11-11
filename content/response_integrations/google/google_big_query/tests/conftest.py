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

from unittest.mock import Mock

import pytest
from TIPCommon.types import SingleJson

import data_models
from google_big_query.core.GoogleBigQueryManager import (
    GoogleBigQueryApiManager,
)
from google_big_query.core.GoogleBigQueryUtils import (
    ExtractConfigurationParameters,
)
from integration_testing.logger import Logger

class BigQueryApiClientMock:
    @staticmethod
    def list_datasets(*_, **__) -> list[Mock]:
        return [Mock(), Mock()]

    @staticmethod
    def query(*_, **__) -> list[SingleJson]:
        return [{"test": "asd"}, {"test": "sdf"}]


class Mockplify:
    LOGGER = Logger()  # pylint: disable=invalid-name

    @staticmethod
    def get_configuration(_) -> SingleJson:
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
    return Mockplify()


@pytest.fixture
def conf_param_extractor() -> ExtractConfigurationParameters:
    return ExtractConfigurationParameters(Mockplify())


@pytest.fixture
def google_sa() -> data_models.GoogleServiceAccount:
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
    return GoogleBigQueryApiManager("project_id", BigQueryApiClientMock())

@pytest.fixture(name='sdk_session', autouse=True)
def sdk_session_fixture(script_session):
    return script_session
