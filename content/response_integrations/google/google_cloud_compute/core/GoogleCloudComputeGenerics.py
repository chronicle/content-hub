from __future__ import annotations

from abc import ABC, abstractmethod
import json

from TIPCommon.base.action import Action
from TIPCommon.base.action.data_models import ExecutionState
from TIPCommon.extraction import extract_action_param, extract_configuration_param
from TIPCommon.utils import is_empty_string_or_none
from TIPCommon.validation import ParameterValidator

from google_cloud_compute.core.GoogleCloudComputeConstants import (
    API_URL,
    INSTANCE_RESOURCE_NAME,
    INTEGRATION_NAME,
    OPERATION_RUNNING_STATUSES,
    FIREWALL_RESOURCE_NAME,
    FIREWALL_RESOURCE_NAME_PATTERN,
    OS_CONFIG_URL,
)
from google_cloud_compute.core.GoogleCloudComputeDatamodels import OperationResource
from google_cloud_compute.core.GoogleCloudComputeExceptions import (
    GoogleCloudComputeInvalidZone,
    GoogleCloudComputeInvalidInstanceID,
    GoogleCloudComputeTimeoutError,
    GoogleCloudComputeValidationError,
)
from google_cloud_compute.core.GoogleCloudComputeManager import GoogleCloudComputeManager
from google_cloud_compute.core.GoogleCloudComputeUtils import (
    extract_instance_resource_path,
    is_async_action_global_timeout_approaching,
)


class BaseGoogleCloudComputeAsyncAction(Action, ABC):
    def __init__(self, script_name: str) -> None:
        super().__init__(script_name)
        self.result_value = self._result_value = False
        self.output_message = ""
        self.json_results = {}
        self.execution_state = ExecutionState.COMPLETED

    def _init_api_clients(self) -> GoogleCloudComputeManager | None:
        return GoogleCloudComputeManager(
            api_root=self.params.api_root,
            os_config_api_root=self.params.os_config_api_root,
            account_type=self.params.account_type,
            project_id=(
                getattr(self.params, "target_project_id", None)
                or self.params.project_id
            ),
            private_key_id=self.params.private_key_id,
            private_key=self.params.private_key,
            client_email=self.params.client_email,
            client_id=self.params.client_id,
            auth_uri=self.params.auth_uri,
            token_uri=self.params.token_uri,
            auth_provider_x509_url=self.params.auth_provider_x509_url,
            client_x509_cert_url=self.params.client_x509_url,
            service_account_json=self.params.service_account_json,
            workload_identity_email=self.params.workload_identity_email,
            verify_ssl=self.params.verify_ssl,
        )

    def _validate_params(self) -> None:
        param_validator = ParameterValidator(self.soar_action)
        if not is_empty_string_or_none(self.params.workload_identity_email):
            param_validator.validate_email(
                param_name="Workload Identity Email",
                email=self.params.workload_identity_email,
            )
        if not is_empty_string_or_none(self.params.service_account_json):
            param_validator.validate_json(
                param_name="Service Account Json File Content",
                json_string=self.params.service_account_json,
                print_value=False,
            )

    def _extract_configuration_params(self) -> None:
        self.params.api_root = extract_configuration_param(
            self.soar_action,
            provider_name=INTEGRATION_NAME,
            param_name="API Root",
            print_value=True,
            default_value=API_URL
        )
        self.params.os_config_api_root = extract_configuration_param(
            self.soar_action,
            provider_name=INTEGRATION_NAME,
            param_name="OS Config API Root",
            print_value=True,
            default_value=OS_CONFIG_URL
        )
        self.params.account_type = extract_configuration_param(
            self.soar_action,
            provider_name=INTEGRATION_NAME,
            param_name="Account Type",
            print_value=True,
        )
        self.params.project_id = extract_configuration_param(
            self.soar_action,
            provider_name=INTEGRATION_NAME,
            param_name="Project ID",
            print_value=True,
        )
        self.params.private_key_id = extract_configuration_param(
            self.soar_action,
            provider_name=INTEGRATION_NAME,
            param_name="Private Key ID",
            remove_whitespaces=False,
        )
        self.params.private_key = extract_configuration_param(
            self.soar_action,
            provider_name=INTEGRATION_NAME,
            param_name="Private Key",
            remove_whitespaces=False,
        )
        self.params.client_email = extract_configuration_param(
            self.soar_action,
            provider_name=INTEGRATION_NAME,
            param_name="Client Email",
            print_value=True,
        )
        self.params.client_id = extract_configuration_param(
            self.soar_action,
            provider_name=INTEGRATION_NAME,
            param_name="Client ID",
            print_value=True,
        )
        self.params.auth_uri = extract_configuration_param(
            self.soar_action,
            provider_name=INTEGRATION_NAME,
            param_name="Auth URI",
            print_value=True,
        )
        self.params.token_uri = extract_configuration_param(
            self.soar_action,
            provider_name=INTEGRATION_NAME,
            param_name="Token URI",
            print_value=True,
        )
        self.params.auth_provider_x509_url = extract_configuration_param(
            self.soar_action,
            provider_name=INTEGRATION_NAME,
            param_name="Auth Provider X509 URL",
            print_value=True,
        )
        self.params.client_x509_url = extract_configuration_param(
            self.soar_action,
            provider_name=INTEGRATION_NAME,
            param_name="Client X509 URL",
            print_value=True,
        )
        self.params.service_account_json = extract_configuration_param(
            self.soar_action,
            provider_name=INTEGRATION_NAME,
            param_name="Service Account Json File Content",
            remove_whitespaces=False,
        )
        self.params.workload_identity_email = extract_configuration_param(
            self.soar_action,
            provider_name=INTEGRATION_NAME,
            param_name="Workload Identity Email",
            print_value=True,
        )
        self.params.verify_ssl = extract_configuration_param(
            self.soar_action,
            provider_name=INTEGRATION_NAME,
            param_name="Verify SSL",
            input_type=bool,
            print_value=True,
        )

    @abstractmethod
    def _extract_action_params(self) -> None:
        """Extract action parameters."""

    def _extract_action_parameters(self):
        self.params.async_context = json.loads(
            extract_action_param(
                self.soar_action, param_name="additional_data", default_value="{}"
            )
        )
        self._extract_configuration_params()
        self._extract_action_params()


class UpdateTagsAction(BaseGoogleCloudComputeAsyncAction, ABC):

    def _validate_params(self) -> None:
        super()._validate_params()
        if not (
            self.params.resource_name
            or (self.params.instance_zone and self.params.instance_id)
        ):
            raise GoogleCloudComputeValidationError(
                "you should provide either 'Resource Name' or "
                "'Instance Zone' and 'Instance ID' parameters"
            )

        param_validator = ParameterValidator(self.soar_action)
        self.params.network_tags_set = set(
            tag.casefold() for tag in
            param_validator.validate_csv(
                param_name="Network Tags",
                csv_string=self.params.network_tags,
                print_value=True,
            )
        )

    def _extract_action_params(self) -> None:
        self.params.resource_name = extract_action_param(
            self.soar_action,
            param_name="Resource Name",
            print_value=True
        )
        self.params.target_project_id = extract_action_param(
            self.soar_action,
            param_name="Project ID",
            input_type=str,
            is_mandatory=False,
            print_value=True,
        )
        self.params.instance_zone = extract_action_param(
            self.soar_action,
            param_name="Instance Zone",
            print_value=True
        )
        self.params.instance_id = extract_action_param(
            self.soar_action,
            param_name="Instance ID",
            print_value=True
        )
        self.params.network_tags = extract_action_param(
            self.soar_action,
            param_name="Network Tags",
            print_value=True,
        )

    @abstractmethod
    def _get_tags(self, existing_tags: set[str]) -> list[str]:
        """Get tags that need to be set for this instance."""

    def _do_first_run_operation(
        self, resource_path: str, manager: GoogleCloudComputeManager
    ) -> OperationResource:
        """Start operations of updating networkInterfaces."""
        instance_data = manager.get_instance(resource_path=resource_path)
        existing_tags = set(instance_data.tags.get("items", []))
        fingerprint = instance_data.tags["fingerprint"]

        return manager.set_instance_tags(
            resource_path=resource_path,
            tags=self._get_tags(existing_tags),
            fingerprint=fingerprint
        )

    @abstractmethod
    def _get_success_message(self, resource_path: str) -> str:
        """Get Success Message of an action."""

    def _get_operation(
            self,
            resource_path: str,
            manager: GoogleCloudComputeManager,
    ):
        """Start operation for first run or query for subsequent runs."""
        if self.is_first_run:
            return self._do_first_run_operation(resource_path, manager)

        operation_link = self.params.async_context
        return manager.get_operation(operation_link)

    def _set_in_progress(
            self,
            resource_path: str,
            operation: OperationResource
    ) -> None:
        """Set action in progress."""
        self._result_value = json.dumps(operation.self_link)
        self.execution_state = ExecutionState.IN_PROGRESS
        self.output_message = (
            f"Waiting for the operation to finish execution on "
            f"the {resource_path} instance in {INTEGRATION_NAME}."
        )

    def _perform_action(self, _=None) -> None:
        manager = self._api_client
        resource_path = (
            extract_instance_resource_path(self.params.resource_name)
            if self.params.resource_name is not None
            else INSTANCE_RESOURCE_NAME.format(
                project_id=manager.project_id,
                zone=self.params.instance_zone,
                resource_id=self.params.instance_id,
            )
        )
        if is_async_action_global_timeout_approaching(
                siemplify=self.soar_action, start_time=self.action_start_time
        ):
            raise GoogleCloudComputeTimeoutError(
                "action ran into a timeout during execution. Please increase "
                "the timeout in IDE."
            )

        try:
            operation = self._get_operation(resource_path, manager)
            if operation.status in OPERATION_RUNNING_STATUSES:
                self._set_in_progress(resource_path, operation)
                return

            operation.raise_for_errors()

            self.result_value = True
            self.json_results = (
                manager.get_instance(resource_path=resource_path).to_json()
            )
            self.output_message = self._get_success_message(resource_path)

        except GoogleCloudComputeInvalidZone as error:
            raise GoogleCloudComputeInvalidZone(
                "provided instance zone is not valid."
            ) from error

        except GoogleCloudComputeInvalidInstanceID as error:
            raise GoogleCloudComputeInvalidInstanceID(
                "provided instance id is not valid."
            ) from error


class UpdateFirewallAction(BaseGoogleCloudComputeAsyncAction, ABC):

    def _validate_params(self) -> None:
        super()._validate_params()
        if not (self.params.resource_name or self.params.firewall_rule):
            raise GoogleCloudComputeValidationError(
                "you should provide either 'Resource name' or "
                "'Firewall Rule Name' parameter"
            )

    def _extract_action_params(self) -> None:
        self.params.resource_name = extract_action_param(
            self.soar_action, param_name="Resource Name", print_value=True
        )
        self.params.target_project_id = extract_action_param(
            self.soar_action,
            param_name="Project ID",
            input_type=str,
            is_mandatory=False,
            print_value=True,
        )
        self.params.firewall_rule = extract_action_param(
            self.soar_action, param_name="Firewall Rule", print_value=True
        )

    @abstractmethod
    def _do_first_run_operation(
            self,
            resource_path: str,
            manager: GoogleCloudComputeManager
    ) -> OperationResource:
        """Start an update firewall operation."""

    def _get_operation_self_link(
            self,
            resource_path: str,
            manager: GoogleCloudComputeManager,
    ) -> str:
        """Start operation for first run or query for subsequent runs."""
        if self.is_first_run:
            update_operation = self._do_first_run_operation(resource_path, manager)
            return update_operation.self_link

        return self.params.async_context["update_operation_self_link"]

    def _set_in_progress(
            self,
            operation: OperationResource,
    ):
        """Set action in progress."""
        self.output_message = (
            f"Updating firewall rule in {INTEGRATION_NAME} service ..."
        )
        self._result_value = json.dumps(
            {"update_operation_self_link": operation.self_link}
        )
        self.execution_state = ExecutionState.IN_PROGRESS

    def _set_success(
            self,
            resource_path: str,
            manager: GoogleCloudComputeManager,
            operation: OperationResource,
    ) -> None:
        """Set action to success state."""
        firewall_rule = manager.get_firewall_rule(resource_path)
        self.json_results = {
            **operation.to_json(),
            "firewall": firewall_rule.to_json()
        }
        self.output_message = (
            f"Successfully updated firewall rule in {INTEGRATION_NAME} service!"
        )
        self.result_value = True

    def _perform_action(self, _=None) -> None:
        manager = self._api_client
        if is_async_action_global_timeout_approaching(
            siemplify=self.soar_action, start_time=self.action_start_time
        ):
            raise GoogleCloudComputeTimeoutError(
                "action ran into a timeout during execution. Please increase "
                "the timeout in IDE."
            )

        resource_path = (
            extract_instance_resource_path(
                self.params.resource_name, FIREWALL_RESOURCE_NAME_PATTERN
            )
            if self.params.resource_name is not None
            else FIREWALL_RESOURCE_NAME.format(
                project_id=manager.project_id, firewall=self.params.firewall_rule
            )
        )

        try:
            update_operation_self_link = self._get_operation_self_link(
                resource_path,
                manager
            )
            operation = manager.get_operation(update_operation_self_link)
            if operation.is_running:
                self._set_in_progress(operation)
                return

            operation.raise_for_errors()
            self._set_success(resource_path, manager, operation)

        except GoogleCloudComputeInvalidInstanceID as error:
            raise GoogleCloudComputeInvalidInstanceID(
                "provided firewall name is not valid."
            ) from error
