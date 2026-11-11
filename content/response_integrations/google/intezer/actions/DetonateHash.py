from __future__ import annotations

from TIPCommon import convert_list_to_comma_string
from TIPCommon.base.action import Action
from TIPCommon.base.utils import validate_manager
from TIPCommon import validation
from TIPCommon.extraction import extract_configuration_param, extract_action_param
from intezer.core import constants
from intezer.core import exceptions
from intezer.core.IntezerManager import IntezerManager


class DetonateFileHash(Action):
    def __init__(self, script_name: str) -> None:
        super().__init__(script_name)
        self.error_output_message = ""
        self.json_results = {}
        self.output_message = ""
        self.result_value = True

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
        self.params.file_hash = extract_action_param(
            self.soar_action, param_name="File Hash", print_value=True
        )

    def _validate_params(self) -> None:
        validator = validation.ParameterValidator(self.soar_action)
        self.params.file_hash = validator.validate_csv(
            param_name="File Hash", csv_string=self.params.file_hash
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

        self.logger.info("Getting the detonate hash details")
        result = []
        self.output_message = ""
        self.result_value = False
        valid_file_hash = []
        invalid_file_hash = []
        file_hash_entity = [
            entity.identifier
            for entity in self.soar_action.target_entities
            if entity.entity_type == constants.FILE_HASH
        ]
        file_hash_entity = file_hash_entity + self.params.file_hash
        for file_hash in set(file_hash_entity):
            try:
                if (
                    len(file_hash) < constants.MD5_LENGTH
                    or len(file_hash) > constants.SHA256_LENGTH
                ):
                    invalid_file_hash.append(file_hash)
                    continue
                response = manager.get_detonate_hash(detonate_hash=file_hash.strip())
                valid_file_hash.append(file_hash)
                result.append(
                    {
                        "analysis_id": response.analysis_id,
                        "analysis_status": response.analysis_status,
                        "analysis_type": response.analysis_type,
                        "identifier": response.identifier,
                    }
                )
            except exceptions.IntezerManagerError:
                invalid_file_hash.append(file_hash)

        self.json_results = result

        if valid_file_hash:
            self.output_message = (
                "Successfully fetched the analysis ids for the following hashes: "
                f"{convert_list_to_comma_string(valid_file_hash)} "
                f"in {constants.INTEGRATION_NAME}\n"
            )
            self.result_value = True

        if invalid_file_hash:
            self.output_message += (
                "Action wasn't able to fetch the analysis ids "
                f"for the following hashes: "
                f"{convert_list_to_comma_string(invalid_file_hash)} "
                f"in {constants.INTEGRATION_NAME}\n"
            )


def main() -> None:
    DetonateFileHash(constants.DETONATE_HASH_SCRIPT_NAME).run()


if __name__ == "__main__":
    main()
