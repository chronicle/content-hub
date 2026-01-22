# Copyright 2025 Google LLC
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

import time
import json
# typings used in python2 type-hints which unrecognized by the linter
from typing import Any, Sequence, Tuple # pylint: disable=unused-import

import requests
import requests.adapters

import google.auth
import google.oauth2
import google.auth.transport.requests
from google.auth import crypt, jwt, impersonated_credentials
from google.auth.credentials import Credentials
from google.oauth2 import service_account, credentials

from ..exceptions import EmptyMandatoryValues, NotFoundError
# typings used in python2 type-hints which unrecognized by the linter
from ..types import ChronicleSOAR, SingleJson   # pylint: disable=unused-import
from ..utils import is_empty_string_or_none


# OOTB Auth Constants
DEFAULT_SCOPES = ['https://www.googleapis.com/auth/cloud-platform']
OOTB_AUTH_ID_SECOPS = 'gcp_ootb_auth'
OOTB_AUTH_KEY_SECOPS = 'siem_sa_email'
DEFAULT_CONTEXT_SCOPE = 0


def generate_jwt_from_sa(service_account_, expiry_length=3600, audience=None):
    # type: (str | SingleJson, int, str | None) -> bytes
    """Generates a Json Web Token to access GCP API resources using REST

    Args:
        service_account (str | dict):
            Google cloud project service account with the necessary IAM roles
        expiry_length (int):
            Time until token expires in seconds. Defaults to 1 hour
        audience (str | None):
            GCP Scope. If not provided, will fall back to
            https://www.googleapis.com/auth/cloud-platform

    Returns:
        bytes: JWT token to use in Authorization header
    """

    if isinstance(service_account_, str):
        service_account_ = json.loads(service_account_)

    if audience is None:
        audience = 'https://www.googleapis.com/auth/cloud-platform'

    sa_email = service_account_.get('client_email')
    now = int(time.time())
    payload = {
        'iat': now,
        'exp': now + expiry_length,
        'iss': sa_email,
        'aud': audience,
        'sub': sa_email,
        'email': sa_email
    }

    signer = crypt.RSASigner.from_service_account_info(service_account_)
    return jwt.encode(signer, payload)


# FIXME: change param name from `credentials` to `credentials_` - regressive
def generate_jwt_from_credentials(credentials, verify_ssl=True):
    # type: (credentials.Credentials, bool) -> bytes
    """Generates a Json Web Token to access GCP API resources using REST

    Args:
        credentials (google.oauth2.credentials.Credentials):
            A `google.oauth2.credentials.Credentials` object
        verify_ssl (bool):
            Whether to refresh the credentials token over SSL.
            Defaults to `True`

    Returns:
        bytes: JWT token to use in Authorization header
    """
    auth_req = google.auth.transport.requests.Request()
    auth_req.session.verify = verify_ssl
    credentials.refresh(auth_req)
    return credentials.token


def get_auth_request(verify_ssl=True):
    # type: (bool) -> google.auth.transport.requests.Request
    """
    Creates an Authorized HTTP request to a GCP resource API.

    Args:
        verify_ssl (bool, optional): Verify SSL certificate. Defaults to True.

    Returns:
        google.auth.transport.requests.Request: An authorized request object
    """
    auth_request_session = requests.Session()
    auth_request_session.verify = verify_ssl

    # Using an adapter to make HTTP requests robust to network errors.
    # This adapter retries HTTP requests when network errors occur
    # and the requests seems safely retryable.
    retry_adapter = requests.adapters.HTTPAdapter(max_retries=3)
    auth_request_session.mount('https://', retry_adapter)
    return google.auth.transport.requests.Request(auth_request_session)


# FIXME: change func name from `get_adc` to `get_app_default_credentials` - regressive
def get_adc(scopes=None, request=None, quota_project_id=None):
    # type: (Sequence[str] | None, google.auth.transport.Request | None, str | None) -> Tuple[Credentials, str | None]
    """Get Application Default Credentials of the runtime environment

    This is a wrapper function for `google.auth.default`

    Args:
        scopes (Sequence[str] | None):
            The list of scopes for the credentials. If specified,
            the credentials will automatically be scoped if necessary.
        request (google.auth.transport.Request | None):
            An object used to make HTTP requests.
            This is used to either detect whether the application is running
            on Compute Engine or to determine the associated project ID for
            a workload identity pool resource (external account credentials).
            If not specified, then it will either use the standard library
            http client to make requests for Compute Engine credentials or a
            `google.auth.transport.requests.Request` client for external
            account credentials.
        quota_project_id (str | None):
            The project ID used for quota and billing.

    Returns:
        Tuple[google.auth.credentials.Credentials, str]:
            the current environment's credentials and project ID.
            Project ID may be None, which indicates that the Project ID
            could not be ascertained from the environment.

    Raises:
        google.auth.exceptions.DefaultCredentialsError:
            If no credentials were found,
            or if the credentials found were invalid.
    """
    return google.auth.default(scopes, request, quota_project_id)


def build_credentials_from_sa(
        user_service_account=None,
        target_principal=None,
        source_credentials=None,
        quota_project_id=None,
        scopes=None,
        verify_ssl=True,
        **service_account_attr
    ):
    # type: (SingleJson | None, str | None, google.auth.credentials.Credentials | None, str | None, list[str] | None , bool | None, Any) -> service_account.Credentials
    """Build credentials object from service account, workload identity email
        or service account attributes

    Note:
        Either service account, workload identity email or service account
        attributes must be provided, otherwise a `EmptyMandatoryValues` exception
        will be raised!

    Args:
        user_service_account (SingleJson | None): User service account json
        target_principal (str | None): Workload identity email
        source_credentials (google.auth.Credentials | None):
            The source credential used as to acquire the impersonated credentials.
            If None provided, will try to use application default credentials.
        quota_project_id (str | None):
            The project ID used for quota and billing.
        scopes (list[str]):
            GCP credentials scopes.
            Defaults to ['https://www.googleapis.com/auth/cloud-platform']
        verify_ssl (bool):
            Whether to verify SSL certificate.
            Defaults to True
        service_account_attr (dict[str, Any]):
            key-value pairs of destructured service account fields

    Raises:
        EmptyMandatoryValues:
            No service account, workload identity email or Missing mandatory 
            fields for service account
        google.auth.exceptions.RefreshError:
            If the credentials could not be refreshed.

    Returns:
        service_account.Credentials: Credentials object
    """
    if (
            user_service_account is None and
            is_empty_string_or_none(target_principal) and
            service_account_attr in [{}, None]
    ):
        raise EmptyMandatoryValues(
            'No service account, workload identity email were provided, or '
            'missing mandatory fields for service account'
        )

    scopes = scopes if scopes is not None else DEFAULT_SCOPES
    if user_service_account is not None:
        return service_account.Credentials.from_service_account_info(
            user_service_account,
            scopes=scopes,
            quota_project_id=quota_project_id
        )
    if not is_empty_string_or_none(target_principal):
        creds = get_impersonated_credentials(
            target_principal=target_principal,
            source_credentials=source_credentials,
            target_scopes=scopes,
            quota_project_id=quota_project_id
        )
        creds.refresh(get_auth_request(verify_ssl=verify_ssl))
        return creds

    return build_credentials_from_sa_attr(
        **service_account_attr,
        scopes=scopes,
        quota_project_id=quota_project_id
    )


def build_credentials_from_sa_attr(
        account_type,
        project_id,
        private_key_id,
        private_key,
        client_email,
        client_id,
        auth_uri,
        token_uri,
        auth_provider_x509_url,
        client_x509_cert_url,
        scopes=None,
        quota_project_id=None
    ):
    # type: (str, str, str, str, str, str, str, str, str, str, list[str] | None, str | None) -> service_account.Credentials
    """Build credentials object from service account attributes

    Args:
        account_type (str): Service account type
        project_id (str): Service account project ID
        private_key_id (str): Service account private key ID
        private_key (str): Service account private key
        client_email (str): Service account client email
        client_id (str): Service account client ID
        auth_uri (str): Service account auth URI
        token_uri (str): Service account token URI
        auth_provider_x509_url (str): Service account auth provider x509 cert URL
        client_x509_cert_url (str): Service account client x509 cert URL
        scopes (list[str], optional): GCP credentials scopes.
            Defaults to ['https://www.googleapis.com/auth/cloud-platform'].
        quota_project_id (str | None):
            The project ID used for quota and billing.

    Raises:
        EmptyMandatoryValues: Missing mandatory fields for service account

    Returns:
        service_account.Credentials: Credentials object
    """
    scopes = scopes if scopes is not None else DEFAULT_SCOPES
    sa_dict = {
        'type': account_type,
        'project_id': project_id,
        'private_key_id': private_key_id,
        'private_key': (
            private_key.replace('\\n', '\n')
            if private_key is not None else None
        ),
        'client_email': client_email,
        'client_id': client_id,
        'auth_uri': auth_uri,
        'token_uri': token_uri,
        'auth_provider_x509_cert_url': auth_provider_x509_url,
        'client_x509_cert_url': client_x509_cert_url
    }
    if all(not is_empty_string_or_none(param) for param in sa_dict.values()):
        return service_account.Credentials.from_service_account_info(
            info=sa_dict,
            scopes=scopes,
            quota_project_id=quota_project_id
        )

    raise EmptyMandatoryValues(
        # pylint:  disable=consider-using-f-string
        'Missing mandatory fields for service account creation: {}'.format(
            ', '.join(
                {
                    param for param, value in sa_dict.items()
                    if is_empty_string_or_none(value)
                }
            )
        )
    )


def get_impersonated_credentials(
    target_principal,
    source_credentials=None,
    target_scopes=None,
    delegates=None,
    quota_project_id=None
):
    # type: (str, google.auth.Credentials | None, Sequence[str] | None, Sequence[str] | None, str | None) -> impersonated_credentials.Credentials
    """Get a short-lived Credentials object using GCP
    ServiceAccount Impersonation

    Args:
        target_principal (str):
            The service account to impersonate.
        source_credentials (google.auth.Credentials | None):
            The source credential used as to acquire the
            impersonated credentials.
            If None provided, will try to use application default credentials.
        target_scopes (Sequence[str] | None):
            Scopes to request during the authorization grant.
            If None provided, will use the default
            'https://www.googleapis.com/auth/cloud-platform' scope.
        delegates (Sequence[str] | None):
            The chained list of delegates required to grant the final
            access_token. If set, the sequence of identities must have
            "Service Account Token Creator" capability granted to the
            prcedeing identity.
            For example, if set to `[serviceAccountB, serviceAccountC]`,
            the source_credential must have the Token Creator role on
            serviceAccountB. serviceAccountB must have the Token Creator on
            serviceAccountC. Finally, C must have Token Creator on
            target_principal. If left unset, source_credential must have that
            role on target_principal.
        quota_project_id (str | None):
            The project ID used for quota and billing.
            This project may be different from the project used to
            create the credentials.

    Returns:
        impersonated_credentials.Credentials:
            A short-lived Credentials object of the target principal
    """
    if target_scopes is None:
        target_scopes = DEFAULT_SCOPES

    if source_credentials is None:
        source_credentials = get_adc()[0]

    return impersonated_credentials.Credentials(
        source_credentials=source_credentials,
        target_principal=target_principal,
        target_scopes=target_scopes,
        delegates=delegates,
        quota_project_id=quota_project_id
    )


def get_secops_siem_tenant_credentials(
    chronicle_soar,
    target_scopes=None,
    quota_project_id=None
):
    # type: (ChronicleSOAR, Sequence[str] | None, str | None) -> impersonated_credentials.Credentials
    """Get the SIEM tenant short-lived service account credentials
    of the SecOps instance

    Args:
        chronicle_soar (TIPCommon.types.ChronicleSOAR):
            ChronicleSOAR SDK object
        target_scopes (Sequence[str] | None):
            Scopes to request during the authorization grant.
        quota_project_id (str | None):
            The project ID used for quota and billing.
            This project may be different from the project used to
            create the credentials.

    Returns:
        impersonated_credentials.Credentials:
            SIEM tenant short-lived service account credentials
    """
    siem_sa_email = chronicle_soar.get_context_property(
        context_type=DEFAULT_CONTEXT_SCOPE,
        identifier=OOTB_AUTH_ID_SECOPS,
        property_key=OOTB_AUTH_KEY_SECOPS
    )
    if is_empty_string_or_none(siem_sa_email):
        raise NotFoundError(
            'SIEM tenant short-lived service account email not found in '
            'SOAR context'
        )

    return get_impersonated_credentials(
        target_principal=siem_sa_email,
        target_scopes=target_scopes,
        quota_project_id=quota_project_id
    )
