from __future__ import annotations

from google.auth.transport.requests import AuthorizedSession
from google.auth.exceptions import RefreshError
import requests
import requests.adapters

from TIPCommon.data_models import GoogleServiceAccount
from TIPCommon.extraction import extract_configuration_param
from TIPCommon.rest.auth import build_credentials_from_sa, get_auth_request
from TIPCommon.rest.gcp import get_workload_sa_email, retrieve_project_id
from TIPCommon.types import ChronicleSOAR
from TIPCommon.utils import is_empty_string_or_none
from TIPCommon.validation import ParameterValidator

from google_gke.core.GKEConsts import API_URL, DEFAULT_LOCATION_ID, INTEGRATION_IDENTIFIER, OAUTH_SCOPES
from google_gke.core.GKEExceptions import GoogleCloudAuthenticationError
from google_gke.core.GKEUtils import parse_string_to_dict


def build_auth_manager(chronicle_soar: ChronicleSOAR) -> GKEAuthManager:
    """
    Extract auth params and build Auth manager.

    Args:
         chronicle_soar: ChronicleSOAR SDK object

    Returns:
        GKE Api manager object
    """
    # Integration configuration
    api_root = extract_configuration_param(
        chronicle_soar,
        provider_name=INTEGRATION_IDENTIFIER,
        param_name="API Root",
        print_value=True,
        default_value=API_URL
    )
    account_type = extract_configuration_param(
        chronicle_soar,
        provider_name=INTEGRATION_IDENTIFIER,
        param_name="Account Type",
        print_value=True,
    )
    project_id = extract_configuration_param(
        chronicle_soar,
        provider_name=INTEGRATION_IDENTIFIER,
        param_name="Project ID",
        print_value=True,
    )
    private_key_id = extract_configuration_param(
        chronicle_soar,
        provider_name=INTEGRATION_IDENTIFIER,
        param_name="Private Key ID",
        remove_whitespaces=False,
    )
    private_key = extract_configuration_param(
        chronicle_soar,
        provider_name=INTEGRATION_IDENTIFIER,
        param_name="Private Key",
        remove_whitespaces=False,
    )
    client_email = extract_configuration_param(
        chronicle_soar,
        provider_name=INTEGRATION_IDENTIFIER,
        param_name="Client Email",
        print_value=True,
    )
    client_id = extract_configuration_param(
        chronicle_soar,
        provider_name=INTEGRATION_IDENTIFIER,
        param_name="Client ID",
        print_value=True,
    )
    auth_uri = extract_configuration_param(
        chronicle_soar,
        provider_name=INTEGRATION_IDENTIFIER,
        param_name="Auth URI",
        print_value=True,
    )
    token_uri = extract_configuration_param(
        chronicle_soar,
        provider_name=INTEGRATION_IDENTIFIER,
        param_name="Token URI",
        print_value=True,
    )
    auth_provider_x509_url = extract_configuration_param(
        chronicle_soar,
        provider_name=INTEGRATION_IDENTIFIER,
        param_name="Auth Provider X509 URL",
        print_value=True,
    )
    client_x509_url = extract_configuration_param(
        chronicle_soar,
        provider_name=INTEGRATION_IDENTIFIER,
        param_name="Client X509 URL",
        print_value=True,
    )
    service_account_json = extract_configuration_param(
        chronicle_soar,
        provider_name=INTEGRATION_IDENTIFIER,
        param_name="Service Account Json File Content",
        remove_whitespaces=False,
    )
    verify_ssl = extract_configuration_param(
        chronicle_soar,
        provider_name=INTEGRATION_IDENTIFIER,
        param_name="Verify SSL",
        input_type=bool,
        print_value=True,
    )
    workload_identity_email = extract_configuration_param(
        chronicle_soar,
        provider_name=INTEGRATION_IDENTIFIER,
        param_name="Workload Identity Email",
        print_value=True,
    )
    location_id = extract_configuration_param(
        chronicle_soar,
        provider_name=INTEGRATION_IDENTIFIER,
        param_name="Location ID",
        is_mandatory=False,
        default_value=DEFAULT_LOCATION_ID,
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

    google_service_account = GoogleServiceAccount(
        account_type=account_type,
        project_id=project_id,
        private_key_id=private_key_id,
        private_key=private_key,
        client_email=client_email,
        client_id=client_id,
        auth_uri=auth_uri,
        token_uri=token_uri,
        auth_provider_x509_url=auth_provider_x509_url,
        client_x509_cert_url=client_x509_url,
    )
    return GKEAuthManager(
        api_root=api_root,
        service_account_json=service_account_json,
        google_service_account=google_service_account,
        workload_identity_email=workload_identity_email,
        location_id=location_id,
        verify_ssl=verify_ssl,
    )


class GKEAuthManager:
    def __init__(
        self,
        api_root: str | None,
        service_account_json: str | dict | None,
        google_service_account: GoogleServiceAccount,
        verify_ssl: bool,
        workload_identity_email: str | None,
        location_id: str,
    ):
        if not is_empty_string_or_none(service_account_json) and not isinstance(
            service_account_json, dict
        ):
            service_account_json = parse_string_to_dict(service_account_json)

        try:
            self.credentials = build_credentials_from_sa(
                user_service_account=service_account_json,
                target_principal=workload_identity_email,
                scopes=OAUTH_SCOPES,
                verify_ssl=verify_ssl,
                **google_service_account.to_dict(),
            )
        except RefreshError as e:
            workload_sa_email = get_workload_sa_email("Unknown Principal")
            raise GoogleCloudAuthenticationError(
                "Impersonation is not allowed for the provided service "
                f"account {workload_identity_email}. "
                'Please add the "Service Account Token Creator" role to the '
                f"service account: {workload_sa_email}"
            ) from e

        project_id = google_service_account.project_id
        if is_empty_string_or_none(google_service_account.project_id):
            project_id = retrieve_project_id(
                service_account_json, workload_identity_email
            )

        self.api_root = api_root
        self.project_id = project_id
        self.verify_ssl = verify_ssl
        self.location_id = location_id

    def prepare_session(self) -> requests.Session:
        """Preparse session object to be used in API session."""
        session = AuthorizedSession(
            self.credentials, auth_request=get_auth_request(verify_ssl=self.verify_ssl)
        )
        session.verify = self.verify_ssl
        return session
