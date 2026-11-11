from __future__ import annotations

import os

from google_threat_intelligence.core.base_action import BaseAction
from google_threat_intelligence.core.constants import (
    DOWNLOAD_FILE_SCRIPT_NAME,
    INTEGRATION_DISPLAY_NAME,
    MD5_LENGTH,
    SHA1_LENGTH,
    SHA256_LENGTH,
)
from google_threat_intelligence.core.exceptions import (
    GoogleThreatIntelligenceExceptions,
    PathNotExistException,
)
from soar_sdk.SiemplifyDataModel import EntityTypes
from TIPCommon.extraction import extract_action_param
from TIPCommon.utils import get_entity_original_identifier
from google_threat_intelligence.core.utils import get_entity_type, save_file

SUPPORTED_ENTITY_TYPES = [
    EntityTypes.FILEHASH,
]

SUCCESS_MESSAGE = (
    "\n Successfully downloaded related files for the following entities in "
)
ERROR_MESSAGE = f"Error executing action {DOWNLOAD_FILE_SCRIPT_NAME}."
NON_RELATED_FILES_ERROR_MESSAGE = (
    "No related files were found for the provided entities."
)
NO_FILES_FOUND_DISPLAY_MSG = "\n Failed to download in "


class DownloadFile(BaseAction):
    def __init__(self, script_name: str) -> None:
        super().__init__(script_name)
        self.output_message = ""
        self.error_output_message = ERROR_MESSAGE
        self.result_value = True
        self.json_results = {}
        self.suitable_entities = [
            entity
            for entity in self._soar_action.target_entities
            if get_entity_type(entity) in SUPPORTED_ENTITY_TYPES
        ]
        self.successful_entities = []
        self.failed_entities = []
        self.absolute_file_paths = []

    def _extract_action_parameters(self) -> None:
        self.params.download_folder_path = extract_action_param(
            self.soar_action,
            param_name="Download Folder Path",
            is_mandatory=True,
            print_value=True,
        )
        self.params.overwrite = extract_action_param(
            self.soar_action,
            param_name="Overwrite",
            print_value=True,
            input_type=bool,
        )

    @staticmethod
    def _is_valid_hash(entity_identifier: str) -> bool:
        return len(entity_identifier) in [
            MD5_LENGTH,
            SHA1_LENGTH,
            SHA256_LENGTH,
        ]

    def _perform_action(self, _=None) -> None:
        """Perform the action for each suitable entity, downloads file content,
        save it, and collects errors for reporting.
        """
        self.api_client.test_connectivity()
        raised_errors: list[str] = []
        all_errors: list[str] = []
        for entity in self.suitable_entities:
            entity_identifier = get_entity_original_identifier(entity)
            self.logger.info(f"Started processing entity: {entity_identifier}")

            if not self._is_valid_hash(entity_identifier=entity_identifier):
                self.logger.error(
                    f"Hash type of hash: {entity_identifier} "
                    "is not supported. Provide either MD5, SHA-256 or SHA-1."
                )
                continue
            try:
                absolute_file_path = self._get_absolute_file_path(entity_identifier)
                if not self.params.overwrite and os.path.exists(absolute_file_path):
                    self._handle_file_error(
                        entity_id=entity_identifier,
                        error=Exception(
                            f"files with path {absolute_file_path} already exist. "
                            f"Please delete the files or set 'Overwrite' to true."
                        ),
                        error_list=raised_errors,
                    )
                    continue

                file_content = self.api_client.get_file(entity_hash=entity_identifier)
                self._save_file(
                    name=entity_identifier,
                    path=absolute_file_path,
                    content=file_content,
                )
            except PathNotExistException as e:
                self._handle_file_error(
                    entity_id=entity_identifier, error=e, error_list=raised_errors
                )
                continue
            except GoogleThreatIntelligenceExceptions as e:
                self._handle_gti_error(
                    entity_id=entity_identifier, error=e, error_list=all_errors
                )
                continue

            self.logger.info(f"Finished processing entity {entity_identifier}")

        self._finalize_action()

        if raised_errors:
            raised_errors.extend(all_errors)
            raise RuntimeError(f"\n{self.output_message}" + "\n".join(raised_errors))

    def _get_absolute_file_path(self, entity_identifier: str) -> str:
        """Constructs absolute file path for the given entity.

        Args:
            entity_identifier: The original identifier of the entity.

        Returns:
            Full file path where the content will be saved.

        """
        return os.path.join(self.params.download_folder_path, entity_identifier)

    def _save_file(self, name: str, path: str, content: str) -> None:
        """Saves the given file content using the save_file function
        and traks the file path and success status.

        Args:
            name: Entity identifier.
            path: Path where the file is saved.
            content: File content to write.

        """
        save_file(
            path=self.params.download_folder_path,
            name=name,
            content=content,
        )
        self.absolute_file_paths.append(path)
        self.successful_entities.append(name)

    def _handle_file_error(
        self, entity_id: str, error: Exception, error_list: list[str]
    ) -> None:
        """Handles file-related exceptions like overwrite or path not existing.

        Args:
            entity_id: The identifier of the entity.
            error: The exception that occurred.
            error_list: List to which formatted error messages are appended.

        """
        self.failed_entities.append(entity_id)
        self.logger.error(f"File operation failed for entity {entity_id}: {error}")
        # We raise these exceptions only when overwrite is False
        error_list.append(f"{type(error).__name__} for entity '{entity_id}': {error}")

    def _handle_gti_error(
        self, entity_id: str, error: Exception, error_list: list[str]
    ):
        """Handles exceptions thrown by GTI API during file fetching.

        Args:
            entity_id: The identifier of the entity.
            error: The exception that occurred.
            error_list: List to which formatted error messages are appended.

        """
        self.failed_entities.append(entity_id)
        self.logger.error(
            f"An error occurred on entity "
            f"{entity_id}. "
            f"Reason: Not found in {INTEGRATION_DISPLAY_NAME}."
        )
        error_list.append(f"{type(error).__name__} for entity '{entity_id}': {error}")

    @staticmethod
    def _format_entities(entities: list[str]) -> str:
        return ", ".join(entities)

    def _finalize_action(self) -> None:
        """Finalizes the action by generating output messages and results
        based on the success or failure of file downloads for entities.
        """

        if self.successful_entities:
            self.json_results = {"absolute_file_paths": self.absolute_file_paths}
            self.output_message += (
                f"{SUCCESS_MESSAGE}"
                f"{INTEGRATION_DISPLAY_NAME}: "
                f"{self._format_entities(self.successful_entities)} \n"
            )
        else:
            self.output_message = NON_RELATED_FILES_ERROR_MESSAGE
            self.result_value = False

        if self.failed_entities:
            self.output_message += (
                f"{NO_FILES_FOUND_DISPLAY_MSG}"
                f"{INTEGRATION_DISPLAY_NAME}: \n "
                f"{self._format_entities(self.failed_entities)} \n"
            )


def main() -> None:
    DownloadFile(DOWNLOAD_FILE_SCRIPT_NAME).run()


if __name__ == "__main__":
    main()
