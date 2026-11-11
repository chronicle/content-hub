from __future__ import annotations

import json
from urllib.parse import urljoin

from google.auth import iam
from google.auth.transport.requests import AuthorizedSession
from google.auth.exceptions import RefreshError
from google.oauth2 import service_account

from TIPCommon.extraction import extract_configuration_param

from TIPCommon.rest.auth import get_auth_request, build_credentials_from_sa
from TIPCommon.rest.gcp import get_workload_sa_email
from TIPCommon.types import ChronicleSOAR
from TIPCommon.utils import is_empty_string_or_none
from TIPCommon.validation import ParameterValidator

from g_suite.core.consts import INTEGRATION_NAME, OAUTH_SCOPES, ENDPOINTS, API_ROOT
from g_suite.core.exceptions import GoogleCloudAuthenticationError, InvalidJSONFormatException
from g_suite.core.utils import parse_string_to_dict


def build_auth_manager(chronicle_soar: ChronicleSOAR) -> GSuiteAuthManager:
    """
    Extract auth params and build Auth manager.

    Args:
         chronicle_soar: ChronicleSOAR SDK object

    Returns:
        Google Gmail Api manager object
    """
    # Integration configuration
    service_account_json = extract_configuration_param(
        chronicle_soar,
        provider_name=INTEGRATION_NAME,
        param_name="Service Account JSON",
        remove_whitespaces=False,
    )
    verify_ssl = extract_configuration_param(
        chronicle_soar,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        input_type=bool,
        print_value=True,
    )
    workload_identity_email = extract_configuration_param(
        chronicle_soar,
        provider_name=INTEGRATION_NAME,
        param_name="Workload Identity Email",
        print_value=True,
    )
    delegated_email = extract_configuration_param(
        chronicle_soar,
        provider_name=INTEGRATION_NAME,
        param_name="Delegated Email",
        is_mandatory=False,
        print_value=True,
    )

    validator = ParameterValidator(chronicle_soar)
    if not is_empty_string_or_none(service_account_json):
        service_account_json = validator.validate_json(
            param_name="Service Account Json File Content",
            json_string=service_account_json,
            print_value=False,
        )
    if not is_empty_string_or_none(workload_identity_email):
        workload_identity_email = validator.validate_email(
            param_name="Workload Identity Email",
            email=workload_identity_email,
            print_value=True,
        )

    return GSuiteAuthManager(
        service_account_creds=service_account_json,
        workload_identity_email=workload_identity_email,
        delegated_email=delegated_email,
        verify_ssl=verify_ssl,
    )


class GSuiteAuthManager:
    def __init__(
        self,
        service_account_creds: str | dict | None,
        workload_identity_email: str | None,
        delegated_email: str | None,
        verify_ssl: bool,
    ):
        self.verify_ssl = verify_ssl

        service_account_json = service_account_creds
        if not is_empty_string_or_none(service_account_creds) and not isinstance(
            service_account_creds, dict
        ):
            try:
                service_account_json = parse_string_to_dict(service_account_creds)
            except InvalidJSONFormatException:
                with open(service_account_creds, encoding="utf-8") as f:
                    service_account_json = json.load(f)

        try:
            credentials = build_credentials_from_sa(
                user_service_account=service_account_json,
                target_principal=workload_identity_email,
                scopes=OAUTH_SCOPES,
                verify_ssl=verify_ssl,
            )

            # Create an IAM signer using the SA credentials.
            signer = iam.Signer(
                get_auth_request(verify_ssl),
                credentials,
                credentials.service_account_email,
            )

            # Create OAuth 2.0 Service Account credentials using the IAM-based
            # signer and the bootstrap_credential's service account email.
            # Impersonate the given subject.
            self.credentials = service_account.Credentials(
                signer,
                credentials.service_account_email,
                "https://accounts.google.com/o/oauth2/token",
                scopes=OAUTH_SCOPES,
                subject=delegated_email,
            )
        except RefreshError as e:
            workload_sa_email = get_workload_sa_email("Unknown Principal")
            raise GoogleCloudAuthenticationError(
                "Impersonation is not allowed for the provided service "
                f"account {workload_identity_email}. "
                'Please add the "Service Account Token Creator" role to the '
                f"service account: {workload_sa_email}"
            ) from e

    def prepare_session(self) -> AuthorizedSession:
        """Preparse session object to be used in API session."""
        session = AuthorizedSession(
            self.credentials, auth_request=get_auth_request(verify_ssl=self.verify_ssl)
        )
        session.verify = self.verify_ssl
        return session

    def _get_full_url(self, url_key, **kwargs) -> str:
        """
        Get full url from url key.
        :param url_id: {str} The key of url
        :param kwargs: {dict} Variables passed for string formatting
        :return: {str} The full url
        """
        return urljoin(API_ROOT, ENDPOINTS[url_key].format(**kwargs))
