from __future__ import annotations

import TIPCommon.validation
from TIPCommon.extraction import extract_configuration_param
from TIPCommon.types import ChronicleSOAR, SingleJson
from google_big_query.core import constants
from google_big_query.core import data_models


class ExtractConfigurationParameters:

    def __init__(self, siemplify: ChronicleSOAR) -> None:
        self.siemplify: ChronicleSOAR = siemplify

    def get_service_account_fields(self) -> data_models.GoogleServiceAccount:
        """Get the integrations configuration service account field params"""
        account_type: str | None = extract_configuration_param(
            self.siemplify,
            provider_name=constants.INTEGRATION_IDENTIFIER,
            param_name="Account Type",
            print_value=True,
        )
        project_id: str | None = extract_configuration_param(
            self.siemplify,
            provider_name=constants.INTEGRATION_IDENTIFIER,
            param_name="Project ID",
            print_value=True,
        )
        private_key_id: str | None = extract_configuration_param(
            self.siemplify,
            provider_name=constants.INTEGRATION_IDENTIFIER,
            param_name="Private Key ID",
            remove_whitespaces=False,
        )
        private_key: str | None = extract_configuration_param(
            self.siemplify,
            provider_name=constants.INTEGRATION_IDENTIFIER,
            param_name="Private Key",
            remove_whitespaces=False,
        )
        client_email: str | None = extract_configuration_param(
            self.siemplify,
            provider_name=constants.INTEGRATION_IDENTIFIER,
            param_name="Client Email",
            print_value=True,
        )
        client_id: str | None = extract_configuration_param(
            self.siemplify,
            provider_name=constants.INTEGRATION_IDENTIFIER,
            param_name="Client ID",
            print_value=True,
        )
        auth_uri: str | None = extract_configuration_param(
            self.siemplify,
            provider_name=constants.INTEGRATION_IDENTIFIER,
            param_name="Auth URI",
            print_value=True,
        )
        token_uri: str | None = extract_configuration_param(
            self.siemplify,
            provider_name=constants.INTEGRATION_IDENTIFIER,
            param_name="Token URI",
            print_value=True,
        )
        auth_provider_x509_url: str | None = extract_configuration_param(
            self.siemplify,
            provider_name=constants.INTEGRATION_IDENTIFIER,
            param_name="Auth Provider X509 URL",
            print_value=True,
        )
        client_x509_url: str | None = extract_configuration_param(
            self.siemplify,
            provider_name=constants.INTEGRATION_IDENTIFIER,
            param_name="Client X509 URL",
            print_value=True,
        )

        return data_models.GoogleServiceAccount(
            account_type=account_type,
            project_id=project_id,
            private_key_id=private_key_id,
            private_key=private_key.replace("\\n", "\n") if private_key else None,
            client_email=client_email,
            client_id=client_id,
            auth_uri=auth_uri,
            token_uri=token_uri,
            client_x509_cert_url=client_x509_url,
            auth_provider_x509_url=auth_provider_x509_url,
        )

    def get_workload_identity_configuration_parameters(
        self,
    ) -> data_models.WorkloadIdentityConfiguration:
        """Get the integration's workload identity configuration parameters"""
        api_root = extract_configuration_param(
            self.siemplify,
            provider_name=constants.INTEGRATION_IDENTIFIER,
            param_name="API Root",
            print_value=True,
        )
        service_account_string = extract_configuration_param(
            self.siemplify,
            provider_name=constants.INTEGRATION_IDENTIFIER,
            param_name="Service Account Json File Content",
            remove_whitespaces=False,
        )
        quota_project_id = extract_configuration_param(
            self.siemplify,
            provider_name=constants.INTEGRATION_IDENTIFIER,
            param_name="Quota Project ID",
            print_value=True,
        )
        workload_identity_email = extract_configuration_param(
            self.siemplify,
            provider_name=constants.INTEGRATION_IDENTIFIER,
            param_name="Workload Identity Email",
            print_value=True,
        )
        verify_ssl = extract_configuration_param(
            self.siemplify,
            provider_name=constants.INTEGRATION_IDENTIFIER,
            param_name="Verify SSL",
            input_type=bool,
            print_value=True,
        )
        wi_email, sa_json = validate_wi_and_sa(
            siemplify=self.siemplify,
            workload_identity_email=workload_identity_email,
            service_account=service_account_string,
        )

        service_account_fields = self.get_service_account_fields()

        return data_models.WorkloadIdentityConfiguration(
            api_root=api_root,
            user_service_account=sa_json,
            service_account_fields=service_account_fields,
            workload_identity_email=wi_email,
            quota_project_id=quota_project_id,
            verify_ssl=verify_ssl,
        )


def validate_wi_and_sa(
    workload_identity_email: str | None,
    service_account: str | None,
    siemplify: ChronicleSOAR,
) -> tuple[str, SingleJson | None]:
    """Validate Workload Identity Email and Service Account

    Args:
        workload_identity_email: The email to validate
        service_account: The service account to validate
        siemplify: The SDK object

    Returns:
        A tuple of the validated and loaded (wi_email, sa_json)
    """
    validator = TIPCommon.validation.ParameterValidator(siemplify)
    if not TIPCommon.utils.is_empty_string_or_none(workload_identity_email):
        workload_identity_email = validator.validate_email(
            param_name="Workload Identity Email", email=workload_identity_email
        )
    service_account_json = None
    if not TIPCommon.utils.is_empty_string_or_none(service_account):
        service_account_json = validator.validate_json(
            param_name="Service Account Json File Content",
            json_string=service_account,
            print_value=False,
        )

    return workload_identity_email, service_account_json
