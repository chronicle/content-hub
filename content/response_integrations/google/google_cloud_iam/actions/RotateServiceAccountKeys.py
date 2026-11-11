from __future__ import annotations

from typing import TYPE_CHECKING

from soar_sdk.SiemplifyDataModel import EntityTypes

from TIPCommon.base.action import Action
from TIPCommon.extraction import extract_action_param
from TIPCommon.transformation import string_to_multi_value

from google_cloud_iam.core.consts import (
    API_URL,
    BAD_REQUEST_STATUS_CODE,
    INTEGRATION_IDENTIFIER,
    MAX_SERVICE_ACCOUNT_KEYS,
    NOT_FOUND_STATUS_CODE,
    ROTATE_SERVICE_ACCOUNT_KEYS_SCRIPT_NAME,
)
from google_cloud_iam.core.exceptions import (
    GoogleCloudIAMManagerError,
    GoogleCloudIAMServiceAccountNotFoundError,
    GoogleCloudIAMValidationError,
)
from google_cloud_iam.core.GoogleCloudIAMManager import GoogleCloudIAMManager
from google_cloud_iam.core.utils import extract_service_account_resource_path

if TYPE_CHECKING:
    from typing import Any

    from TIPCommon.types import SingleJson

    AnyList = list[Any]


SUPPORTED_ENTITIES = [EntityTypes.USER, EntityTypes.DEPLOYMENT]


class RotateServiceAccountKeysAction(Action):

    def __init__(self, script_name: str) -> None:
        super().__init__(script_name)
        self.json_results: list[SingleJson] = []
        self.successful_entities: list[str] = []
        self.failed_entities: list[str] = []
        self.not_found_entities: list[str] = []

    def _extract_parameters(self) -> None:
        self.params.service_accounts = extract_action_param(
            self.soar_action,
            param_name="Service Account",
            is_mandatory=False,
            print_value=True,
            default_value="",
        )
        self.params.api_root = self.soar_action.extract_configuration_param(
            provider_name=INTEGRATION_IDENTIFIER,
            param_name="API Root",
            print_value=True,
            default_value=API_URL,
        )
        self.params.account_type = self.soar_action.extract_configuration_param(
            provider_name=INTEGRATION_IDENTIFIER,
            param_name="Account Type",
            print_value=True,
        )
        self.params.project_id = self.soar_action.extract_configuration_param(
            provider_name=INTEGRATION_IDENTIFIER,
            param_name="Project ID",
            print_value=True,
        )
        self.params.quota_project_id = self.soar_action.extract_configuration_param(
            provider_name=INTEGRATION_IDENTIFIER,
            param_name="Quota Project ID",
            print_value=True,
        )
        self.params.private_key_id = self.soar_action.extract_configuration_param(
            provider_name=INTEGRATION_IDENTIFIER,
            param_name="Private Key ID",
        )
        self.params.private_key = self.soar_action.extract_configuration_param(
            provider_name=INTEGRATION_IDENTIFIER,
            param_name="Private Key",
        )
        self.params.client_email = self.soar_action.extract_configuration_param(
            provider_name=INTEGRATION_IDENTIFIER,
            param_name="Client Email",
            print_value=True,
        )
        self.params.client_id = self.soar_action.extract_configuration_param(
            provider_name=INTEGRATION_IDENTIFIER,
            param_name="Client ID",
            print_value=True,
        )
        self.params.auth_uri = self.soar_action.extract_configuration_param(
            provider_name=INTEGRATION_IDENTIFIER,
            param_name="Auth URI",
            print_value=True,
        )
        self.params.token_uri = self.soar_action.extract_configuration_param(
            provider_name=INTEGRATION_IDENTIFIER,
            param_name="Token URI",
            print_value=True,
        )
        self.params.auth_provider_x509_url = (
            self.soar_action.extract_configuration_param(
                provider_name=INTEGRATION_IDENTIFIER,
                param_name="Auth Provider X509 URL",
                print_value=True,
            )
        )
        self.params.client_x509_cert_url = self.soar_action.extract_configuration_param(
            provider_name=INTEGRATION_IDENTIFIER,
            param_name="Client X509 URL",
            print_value=True,
        )
        self.params.organization_id = self.soar_action.extract_configuration_param(
            provider_name=INTEGRATION_IDENTIFIER,
            param_name="Organization ID",
            print_value=True,
        )
        self.params.service_account_json = self.soar_action.extract_configuration_param(
            provider_name=INTEGRATION_IDENTIFIER,
            param_name="Service Account Json File Content",
        )
        self.params.verify_ssl = self.soar_action.extract_configuration_param(
            provider_name=INTEGRATION_IDENTIFIER,
            param_name="Verify SSL",
            input_type=bool,
            print_value=True,
        )
        self.params.workload_identity_email = (
            self.soar_action.extract_configuration_param(
                provider_name=INTEGRATION_IDENTIFIER,
                param_name="Workload Identity Email",
                print_value=True,
            )
        )

    def _validate_params(self) -> None:
        pass

    def _init_managers(self) -> None:
        self.api_client: GoogleCloudIAMManager = GoogleCloudIAMManager(
            siemplify=self.soar_action,
            api_root=self.params.api_root,
            account_type=self.params.account_type,
            project_id=self.params.project_id,
            quota_project_id=self.params.quota_project_id,
            private_key_id=self.params.private_key_id,
            private_key=self.params.private_key,
            client_email=self.params.client_email,
            client_id=self.params.client_id,
            auth_uri=self.params.auth_uri,
            token_uri=self.params.token_uri,
            auth_provider_x509_url=self.params.auth_provider_x509_url,
            client_x509_cert_url=self.params.client_x509_cert_url,
            organization_id=self.params.organization_id,
            service_account_json=self.params.service_account_json,
            verify_ssl=self.params.verify_ssl,
            workload_identity_email=self.params.workload_identity_email,
        )

    def _perform_action(self, _manager: GoogleCloudIAMManager) -> None:
        supported_entities: AnyList = self._get_supported_entities()

        if not supported_entities:
            self.output_message = "No service accounts provided to rotate keys."
            self.result_value = True
            return

        for entity in supported_entities:
            self._process_entity(entity)

        self._build_output_and_set_result(bool(supported_entities))

        if self.json_results:
            self.soar_action.result.add_result_json(self.json_results)

        if self.failed_entities:
            raise RuntimeError(self.output_message)

    def _process_entity(self, entity: Any) -> None:
        entity_identifier: str = (
            entity if isinstance(entity, str) else entity.identifier
        )
        self.logger.info(
            f"Started processing service account: {entity_identifier}"
        )

        try:
            project_id, sa_id = self._extract_account_details(entity_identifier)
            new_key: Any = self._rotate_keys_for_account(sa_id, project_id)
            self.successful_entities.append(entity_identifier)
            self.json_results.append({
                "Entity": entity_identifier,
                "EntityResult": new_key.to_json()
            })
        except GoogleCloudIAMServiceAccountNotFoundError as e:
            self.not_found_entities.append(entity_identifier)
            self.logger.error(f"Error processing '{entity_identifier}': {e}")
        except RuntimeError:
            self.failed_entities.append(entity_identifier)
            self.logger.error(
                f"Failed to process service account '{entity_identifier}'."
            )

    def _extract_account_details(
        self,
        identifier: str,
    ) -> tuple[str | None, str]:
        try:
            project_id, sa_id = extract_service_account_resource_path(
                identifier.lower()
            )
            self.logger.info(
                f"Extracted project '{project_id}' from identifier."
            )
            return project_id, sa_id
        except GoogleCloudIAMValidationError:
            self.logger.info(
                "Identifier is not a full resource path, using it as "
                "service account email."
            )
            return None, identifier

    def _delete_remaining_old_keys(
        self,
        keys: AnyList,
        sa_id: str,
    ) -> None:
        if not keys:
            return

        self.logger.info(f"Deleting {len(keys)} old key(s) for '{sa_id}'.")
        for key in keys:
            self.api_client.delete_service_account_key(key_name=key.name)
        self.logger.info(f"Successfully deleted old keys for '{sa_id}'.")

    def _get_existing_keys(
        self,
        sa_id: str,
        project_id: str | None,
    ) -> AnyList:
        try:
            existing_keys: AnyList = self.api_client.get_service_account_keys(
                sa_identifier=sa_id,
                sa_project=project_id,
            )
            self.logger.info(
                f"Found {len(existing_keys)} existing keys for '{sa_id}'."
            )
            return existing_keys
        except GoogleCloudIAMManagerError as e:
            if str(NOT_FOUND_STATUS_CODE) in str(e):
                raise GoogleCloudIAMServiceAccountNotFoundError(e) from e
            raise

    def _create_key_with_limit_handling(
        self,
        sa_id: str,
        existing_keys: AnyList,
    ) -> tuple[Any, AnyList]:
        try:
            new_key: Any = self._try_create_key(sa_id)
            return new_key, existing_keys
        except GoogleCloudIAMManagerError as e:
            is_bad_request: bool = str(BAD_REQUEST_STATUS_CODE) in str(e)
            is_at_key_limit: bool = len(existing_keys) >= MAX_SERVICE_ACCOUNT_KEYS

            if is_bad_request and is_at_key_limit:
                return self._handle_key_limit_reached(sa_id, existing_keys)

            raise

    def _handle_key_limit_reached(
        self,
        sa_id: str,
        existing_keys: AnyList,
    ) -> tuple[Any, AnyList]:
        self.logger.info(
            f"Key limit of {MAX_SERVICE_ACCOUNT_KEYS} reached for '{sa_id}'. "
            f"Deleting the oldest key to make space."
        )
        oldest_key: Any = min(existing_keys, key=lambda k: k.valid_after_time)

        self.api_client.delete_service_account_key(key_name=oldest_key.name)
        self.logger.info(
            f"Successfully deleted oldest key '{oldest_key.name}'. "
            f"Retrying key creation."
        )
        existing_keys.remove(oldest_key)

        new_key: Any = self._try_create_key(sa_id)

        return new_key, existing_keys

    def _try_create_key(self, sa_id: str) -> Any:
        self.logger.info(f"Creating new key for '{sa_id}'.")
        new_key: Any = self.api_client.create_service_account_key(
            service_account_email=sa_id
        )
        self.logger.info(f"Successfully created new key '{new_key.name}'.")

        return new_key

    def _rotate_keys_for_account(
        self,
        sa_id: str,
        project_id: str | None,
    ) -> Any:
        existing_keys: AnyList = self._get_existing_keys(sa_id, project_id)

        new_key: Any
        keys_to_delete: AnyList
        new_key, keys_to_delete = self._create_key_with_limit_handling(
            sa_id, existing_keys
        )

        self._delete_remaining_old_keys(keys_to_delete, sa_id)

        return new_key

    def _build_status_messages(self) -> list[str]:
        messages: list[str] = []
        if self.successful_entities:
            messages.append(
                "Successfully rotated keys for service accounts "
                f"{', '.join(self.successful_entities)} in Google Cloud IAM.\n"
            )

        if self.not_found_entities:
            messages.append(
                "The following service accounts were not found in Google "
                f"Cloud IAM: {', '.join(self.not_found_entities)}\n"
            )

        if self.failed_entities:
            messages.append(
                "An error occurred while rotating keys for the following "
                f"service accounts: {', '.join(self.failed_entities)}\n"
            )

        return messages

    def _build_output_and_set_result(self, has_supported_entities: bool) -> None:
        self.result_value = not self.failed_entities
        status_messages: list[str] = self._build_status_messages()
        self.output_message = "\n".join(status_messages)

        all_not_found: bool = (
            not self.successful_entities
            and not self.failed_entities
            and self.not_found_entities
        )
        nothing_processed: bool = not self.output_message

        if all_not_found:
            self.output_message = (
                "None of the provided service accounts were found in "
                "Google Cloud IAM."
            )
            self.result_value = False
        elif nothing_processed:
            self.output_message = "No service accounts were processed."
            self.result_value = not has_supported_entities

    def _get_soar_entities(self) -> AnyList:
        return [
            entity
            for entity in self.soar_action.target_entities
            if entity.entity_type in SUPPORTED_ENTITIES
        ]

    def _get_supported_entities(self) -> AnyList:
        soar_entities: AnyList = self._get_soar_entities()
        param_entities: list[str] = string_to_multi_value(
            string_value=self.params.service_accounts,
        )

        all_entities: AnyList = []
        processed_sa_emails: set[str] = set()

        for entity in soar_entities + param_entities:
            identifier: str = (
                entity.identifier if not isinstance(entity, str) else entity
            ).strip()

            if not identifier:
                continue

            try:
                sa_email: str
                _, sa_email = extract_service_account_resource_path(identifier.lower())
            except GoogleCloudIAMValidationError:
                sa_email = identifier

            sa_email_key: str = sa_email.casefold()

            if sa_email_key not in processed_sa_emails:
                all_entities.append(entity)
                processed_sa_emails.add(sa_email_key)

        return all_entities


def main() -> None:
    action = RotateServiceAccountKeysAction(
        ROTATE_SERVICE_ACCOUNT_KEYS_SCRIPT_NAME,
    )
    action.run()


if __name__ == "__main__":
    main()
