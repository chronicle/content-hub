from __future__ import annotations

import unittest.mock

import google.auth.credentials
import google.cloud.bigquery
import pytest
import requests

from TIPCommon.types import SingleJson

import data_models
from google_big_query.core.authentication import (
    create_session,
    get_auth_credentials_or_raise_error,
    GoogleBigQueryExceptions,
)


class TestCreateSession:

    @pytest.mark.parametrize("verify_ssl", [True, False])
    def test_create_session(
        self,
        verify_ssl: bool,
    ) -> None:
        with unittest.mock.patch(
            "google.auth.transport.requests.AuthorizedSession",
            return_value=requests.Session(),
        ):
            session: google.cloud.bigquery.Client = create_session(
                api_root="",
                credentials=google.auth.credentials.Credentials,
                project_id="project_id",
                verify_ssl=verify_ssl,
            )
            assert isinstance(session, google.cloud.bigquery.Client)


class TestGetAuthCredentials:

    @pytest.mark.parametrize(
        "user_service_account, workload_identity_email, verify_ssl",
        [
            ({"type": "service_account"}, None, True),
            ({"type": "service_account"}, None, False),
            (None, "workload_identity_email", True),
            (None, "workload_identity_email", False),
        ],
    )
    def test_get_authentication_credentials_or_raise_error(
        self,
        user_service_account: SingleJson | None,
        workload_identity_email: str,
        verify_ssl: bool,
        google_sa: data_models.GoogleServiceAccount,
    ) -> None:
        wi_conf = data_models.WorkloadIdentityConfiguration(
            api_root="",
            user_service_account=user_service_account,
            workload_identity_email=workload_identity_email,
            verify_ssl=verify_ssl,
            quota_project_id="",
            service_account_fields=google_sa,
        )
        with unittest.mock.patch(
            "TIPCommon.rest.auth.build_credentials_from_sa",
            return_value=google.auth.credentials.Credentials,
        ):
            credentials = get_auth_credentials_or_raise_error(wi_conf)

        assert credentials is not None

    @pytest.mark.parametrize("verify_ssl", [True, False])
    def test_get_credentials_without_enough_data_raise_validation_error(
        self,
        verify_ssl: bool,
        empty_google_sa: data_models.GoogleServiceAccount,
    ) -> None:
        wi_conf = data_models.WorkloadIdentityConfiguration(
            api_root="",
            user_service_account=None,
            workload_identity_email="",
            verify_ssl=verify_ssl,
            quota_project_id="",
            service_account_fields=empty_google_sa,
        )
        with pytest.raises(GoogleBigQueryExceptions.GoogleBigQueryValidationError):
            _ = get_auth_credentials_or_raise_error(wi_conf)
