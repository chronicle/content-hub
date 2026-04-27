from __future__ import annotations

from google.cloud.storage.constants import PUBLIC_ACCESS_PREVENTION_ENFORCED

from TIPCommon import validation
from TIPCommon.base.action import Action
from TIPCommon.base.utils import validate_manager
from TIPCommon.extraction import extract_configuration_param, extract_action_param
from TIPCommon.utils import is_empty_string_or_none

from ..core.consts import INTEGRATION_NAME, REMOVE_PUBLIC_ACCESS_FROM_BUCKET
from ..core.GoogleCloudStorageManager import GoogleCloudStorageManager


class RemovePublicAccessFromBucket(Action):
    def __init__(self, script_name: str) -> None:
        super().__init__(script_name)
        self.output_message = ""
        self.error_output_message = (
            f'Error executing action: "{REMOVE_PUBLIC_ACCESS_FROM_BUCKET}".'
        )
        self.result_value = False

    def _extract_parameters(self) -> None:
        # configuration parameters
        self.params.service_account = extract_configuration_param(
            self.soar_action,
            provider_name=INTEGRATION_NAME,
            param_name="Service Account",
        )
        self.params.workload_identity_email = extract_configuration_param(
            self.soar_action,
            provider_name=INTEGRATION_NAME,
            param_name="Workload Identity Email",
        )
        self.params.api_root = extract_configuration_param(
            self.soar_action,
            provider_name=INTEGRATION_NAME,
            param_name="API Root",
        )
        self.params.project_id = extract_configuration_param(
            self.soar_action, provider_name=INTEGRATION_NAME, param_name="Project ID"
        )
        self.params.quota_project_id = extract_configuration_param(
            self.soar_action,
            provider_name=INTEGRATION_NAME,
            param_name="Quota Project ID",
        )
        self.params.verify_ssl = extract_configuration_param(
            self.soar_action,
            provider_name=INTEGRATION_NAME,
            param_name="Verify SSL",
            input_type=bool,
        )

        # action parameters
        self.params.resource_name = extract_action_param(
            self.soar_action,
            param_name="Resource Name",
            is_mandatory=True,
            print_value=True,
        )
        self.params.prevent_public_access_from_bucket = extract_action_param(
            self.soar_action,
            param_name="Prevent Public Access From Bucket",
            is_mandatory=True,
            input_type=bool,
            print_value=True,
        )

    def _validate_params(self) -> None:
        validator = validation.ParameterValidator(self.soar_action)

        if not is_empty_string_or_none(self.params.service_account):
            self.params.service_account = validator.validate_json(
                param_name="Service Account",
                json_string=self.params.service_account,
                print_value=False,
            )

        if not is_empty_string_or_none(self.params.workload_identity_email):
            self.params.workload_identity_email = validator.validate_email(
                param_name="Workload Identity Email",
                email=self.params.workload_identity_email,
                print_value=True,
            )

    def _init_managers(self) -> GoogleCloudStorageManager:
        return GoogleCloudStorageManager(
            service_account=self.params.service_account,
            workload_identity_email=self.params.workload_identity_email,
            api_root=self.params.api_root,
            project_id=self.params.project_id,
            quota_project_id=self.params.quota_project_id,
            verify_ssl=self.params.verify_ssl,
            logger=self.soar_action.logger,
        )

    def _perform_action(self, manager: GoogleCloudStorageManager, _=None) -> None:
        self.logger.info("Validating manager is not None")
        validate_manager(manager)

        bucket = manager.get_bucket(bucket_name=self.params.resource_name)
        manager.remove_public_access(bucket=bucket.bucket_data)

        if self.params.prevent_public_access_from_bucket:
            manager.update_public_access_prevention(
                bucket=bucket.bucket_data, value=PUBLIC_ACCESS_PREVENTION_ENFORCED
            )

        self.result_value = True
        self.output_message = (
            f"Successfully removed public access from bucket using Google Cloud "
            f"Storage: {self.params.resource_name}."
        )


def main() -> None:
    RemovePublicAccessFromBucket(REMOVE_PUBLIC_ACCESS_FROM_BUCKET).run()


if __name__ == "__main__":
    main()
