from __future__ import annotations

from TIPCommon import convert_list_to_comma_string
from TIPCommon.base.action import Action
from TIPCommon.base.utils import validate_manager
from TIPCommon import validation
from TIPCommon.extraction import extract_configuration_param, extract_action_param
from intezer.core import constants
from intezer.core import exceptions
from intezer.core.IntezerManager import IntezerManager


class UnsetIndexFile(Action):
    def __init__(self, script_name: str) -> None:
        super().__init__(script_name)
        self.error_output_message = ""
        self.json_results = {}
        self.output_message = ""
        self.result_value = False

    def _extract_parameters(self) -> None:
        # Configuration Parameters
        self.params.api_root = extract_configuration_param(
            self.soar_action,
            provider_name=constants.INTEGRATION_NAME,
            param_name="API Root",
            is_mandatory=True,
            print_value=True,
        )
        self.params.api_key = extract_configuration_param(
            self.soar_action,
            provider_name=constants.INTEGRATION_NAME,
            param_name="API key",
            is_mandatory=True,
            print_value=False,
            remove_whitespaces=False,
        )
        self.params.verify_ssl = extract_configuration_param(
            self.soar_action,
            provider_name=constants.INTEGRATION_NAME,
            param_name="Verify SSL",
            is_mandatory=True,
            input_type=bool,
            print_value=True,
        )

        # Action Parameters
        self.params.sha256 = extract_action_param(
            self.soar_action, param_name="SHA256", print_value=True
        )

    def _validate_params(self) -> None:
        validator = validation.ParameterValidator(self.soar_action)
        self.params.sha256 = validator.validate_csv(
            param_name="SHA256", csv_string=self.params.sha256
        )

    def _init_managers(self) -> IntezerManager:
        return IntezerManager(
            api_root=self.params.api_root,
            api_key=self.params.api_key,
            verify_ssl=self.params.verify_ssl,
            siemplify_logger=self.logger,
        )

    def _perform_action(self, manager: IntezerManager, _=None) -> None:
        self.logger.info("Validating manager is not None")
        validate_manager(manager)

        valid_sha256 = []
        invalid_sha256 = []
        hash_entity = [
            entity.identifier
            for entity in self.soar_action.target_entities
            if entity.entity_type == constants.FILE_HASH
        ]
        sha256_with_hash = hash_entity + self.params.sha256
        for sha256 in set(sha256_with_hash):
            try:
                manager.unset_index_file(sha256=sha256.strip())
                valid_sha256.append(sha256)
            except (exceptions.IntezerManagerError, exceptions.IntezerNotFoundError):
                invalid_sha256.append(sha256)

        if valid_sha256:
            self.output_message = (
                "Successfully unset file index for the following hashes: "
                f"{convert_list_to_comma_string(valid_sha256)} "
                f"in {constants.INTEGRATION_NAME}\n"
            )
            self.result_value = True

        if invalid_sha256:
            self.output_message += (
                "Action wasn't able to unset file index for the following hashes: "
                f"{convert_list_to_comma_string(invalid_sha256)} "
                f"in {constants.INTEGRATION_NAME}\n"
            )


def main() -> None:
    UnsetIndexFile(constants.UNSET_INDEX_FILE_SCRIPT_NAME).run()


if __name__ == "__main__":
    main()
