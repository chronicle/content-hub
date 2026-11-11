from __future__ import annotations

import io
import json
from google_threat_intelligence.core import data_models
from google_threat_intelligence.core.base_action import BaseAction
from google_threat_intelligence.core.constants import (
    COMPLETED,
    ENTITY_TYPE_MAP,
    SUBMIT_FILE_SCRIPT_NAME,
)
from google_threat_intelligence.core.exceptions import (
    GoogleThreatIntelligenceExceptions,
    GoogleThreatIntelligenceHTTPException,
    ParamsValidationException,
)
from google_threat_intelligence.core.files_manager import FileManager
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyUtils import convert_dict_to_json_result_dict, unix_now
from TIPCommon import validation
from TIPCommon.base.action.data_models import ExecutionState
from TIPCommon.extraction import extract_action_param
from TIPCommon.transformation import construct_csv
from google_threat_intelligence.core.utils import Enricher, assess_risk, convert_days_to_milliseconds

ERROR_MESSAGE = f"Error executing action {SUBMIT_FILE_SCRIPT_NAME}."
ERROR_NO_ENTITIES_MESSAGE = (
    "Error executing action “Submit File”. "
    "Reason: at least one of “File Paths” or "
    "“External URLs” parameters should have a value."
)


class SubmitFile(BaseAction):
    """Action to handle the submission of files for analysis.

    Initializes result, state indicators, and placeholders for results.
    """

    def __init__(self, script_name: str) -> None:
        """Initialize the SubmitFile action.

        Args:
             script_name: The name of script to be executed.

        """
        super().__init__(script_name)
        self.output_message = ""
        self.error_output_message = ERROR_MESSAGE
        self.execution_state = ExecutionState.COMPLETED
        self.json_results = {}
        self.successful_files = []
        self.failed_files = []
        self._result_value = self.result_value = True
        self.analysis_ids = {}
        self.files_hash = {}
        self.files_result_data = {}
        self.entities_existing_data = {}
        self.failed_entities = []

    def _extract_action_parameters(self) -> None:
        self.params.files_str = extract_action_param(
            self.soar_action,
            param_name="File Paths",
            remove_whitespaces=False,
            is_mandatory=False,
            print_value=True,
        )
        self.params.external_urls = extract_action_param(
            self.soar_action,
            param_name="External URLs",
            is_mandatory=False,
            print_value=True,
        )

        self.params.private_submission = extract_action_param(
            self.soar_action,
            param_name="Private Submission",
            is_mandatory=False,
            input_type=bool,
            print_value=True,
        )

        self.params.fetch_mitre_details = extract_action_param(
            self.soar_action,
            param_name="Fetch MITRE Details",
            print_value=True,
            input_type=bool,
        )

        self.params.check_hash_first = extract_action_param(
            self.soar_action,
            param_name="Check Hash First",
            print_value=True,
            input_type=bool,
        )

        self.params.gti_score = extract_action_param(
            self.soar_action,
            param_name="GTI Score",
            print_value=True,
            input_type=int,
        )

        self.params.engine_threshold = extract_action_param(
            self.soar_action,
            param_name="Engine Threshold",
            print_value=True,
            input_type=int,
        )

        self.params.engine_percentage_threshold = extract_action_param(
            self.soar_action,
            param_name="Engine Percentage Threshold",
            print_value=True,
            input_type=int,
        )

        self.params.engine_allowlist = extract_action_param(
            self.soar_action,
            param_name="Engine Allowlist",
            print_value=True,
            default_value="",
        )

        self.params.resubmit_after_days = extract_action_param(
            self.soar_action,
            param_name="Resubmit After (Days)",
            print_value=True,
            input_type=int,
            default_value=30,
        )

        self.params.lowest_mitre_severity = extract_action_param(
            self.soar_action,
            param_name="Lowest MITRE Technique Severity",
            print_value=True,
            default_value="Medium",
        ).upper()

        self.params.retrieve_comments = extract_action_param(
            self.soar_action,
            param_name="Retrieve Comments",
            print_value=True,
            input_type=bool,
        )

        self.params.max_comments_to_return = extract_action_param(
            self.soar_action,
            param_name="Max Comments To Return",
            print_value=True,
            default_value="10",
        )

        self.params.server_address = extract_action_param(
            self.soar_action,
            param_name="Linux Server Address",
            is_mandatory=False,
            print_value=True,
        )

        self.params.server_username = extract_action_param(
            self.soar_action,
            param_name="Linux Username",
            is_mandatory=False,
            print_value=True,
        )

        self.params.server_password = extract_action_param(
            self.soar_action,
            param_name="Linux Password",
            is_mandatory=False,
            print_value=True,
        )

        self.params.zip_password = extract_action_param(
            self.soar_action,
            param_name="ZIP Password",
            is_mandatory=False,
            print_value=True,
        )

        self.params.additional_data = json.loads(
            extract_action_param(self.soar_action, "additional_data", "{}")
        )

    def _validate_params(self) -> None:
        validator = validation.ParameterValidator(self.soar_action)

        self.params.files_str = validator.validate_csv(
            param_name="File Paths",
            csv_string=self.params.files_str,
            print_value=True,
        )
        self.params.external_urls = validator.validate_csv(
            param_name="External URLs",
            csv_string=self.params.external_urls,
            print_value=True,
        )

        if self.params.gti_score:
            self.params.gti_score = validator.validate_percentage(
                param_name="GTI Score",
                value=self.params.gti_score,
                print_value=False,
            )

        if self.params.engine_threshold:
            self.params.engine_threshold = validator.validate_non_negative(
                param_name="Engine Threshold",
                value=self.params.engine_threshold,
                print_value=False,
            )

        if self.params.engine_percentage_threshold:
            self.params.engine_percentage_threshold = validator.validate_percentage(
                param_name="Engine Percentage Threshold",
                value=self.params.engine_percentage_threshold,
                print_value=False,
            )

        self.params.engine_allowlist = validator.validate_csv(
            param_name="Engine Allowlist",
            csv_string=self.params.engine_allowlist,
            print_value=False,
        )

        if (
            self.params.engine_allowlist
            and self.params.engine_threshold
            and len(self.params.engine_allowlist) < self.params.engine_threshold
        ):
            raise ParamsValidationException(
                "Engine threshold cannot be greater than engine allowlist length"
            )

        if self.params.resubmit_after_days:
            self.params.resubmit_after_days = validator.validate_non_negative(
                param_name="Resubmit After (Days)",
                value=self.params.resubmit_after_days,
                print_value=False,
            )

        self.params.max_comments_to_return = validator.validate_positive(
            param_name="Max Comments To Return",
            value=self.params.max_comments_to_return,
            print_value=False,
        )

    def _get_zip_password(
        self,
        file_manager: FileManager,
        file_path: str,
    ) -> str | None:
        """Retrieve the ZIP password if the provided file is ZIP folder
        and password is set in the parameters.

        Args:
            file_manager:
            An instance of FileManager to check the file type.
            file_path: The path to the file to check.

        Returns:
            Optional[str]:The password if available and the file is ZIP, otherwise None.

        """
        password: str | None = None
        if self.params.zip_password and file_manager.is_zip_folder(
            folder_path=file_path
        ):
            password = self.params.zip_password
        return password

    @staticmethod
    def _format_error_message(error: Exception) -> str:
        """Format an error message for logging or display"""
        return f"Error executing action Submit File. Reason: {error!s}"

    def _fetch_file_ioc_details(
        self, file_hash: str, is_private: bool
    ) -> data_models.Hash | None:
        try:
            return self.api_client.get_ioc_details(
                ioc=file_hash,
                ioc_type=ENTITY_TYPE_MAP.get(EntityTypes.FILEHASH),
                is_private_submission=is_private,
            )
        except GoogleThreatIntelligenceExceptions as err:
            self.logger.info(f"File not found: {file_hash}. Error: {err}")
            return None

    def check_hash_existence(self, file_hash: str) -> data_models.FileHashExistence:
        """Check whether the given file hash exists in public and/or private submission.

        Args:
            file_hash: The file hash to check.

        Returns:
              FileHashExistence: An object containing information
              about the existence of the file hash.

        """
        ioc_details = self._fetch_file_ioc_details(
            file_hash=file_hash, is_private=False
        )
        exists_public = ioc_details is not None
        exists_private = False
        if not exists_public:
            ioc_details = self._fetch_file_ioc_details(
                file_hash=file_hash, is_private=True
            )
            exists_private = ioc_details is not None
        return data_models.FileHashExistence(
            exists_public=exists_public,
            exists_private=exists_private,
            file_hash=file_hash,
            last_submission_date=ioc_details.last_analysis_date if ioc_details else 0,
        )

    def _is_report_outdated(self, file_hash_existence: data_models.FileHashExistence):
        return (
            unix_now() - convert_days_to_milliseconds(self.params.resubmit_after_days)
            > file_hash_existence.last_submission_date * 1000
        )

    def submit_file(
        self,
        file_path: str,
        file_content: bytes,
        file_manager: FileManager,
        password: str | None = None,
    ) -> str | None:
        """Submit a file for analysis.
        If the file is already known, use its hash,
        otherwise, upload it and then submit.

        Args:
            file_path: The file path.
            file_content: The file content to be submitted.
            file_manager: The file manager instance used to fetch remote files.
            password: The password for zip archive.

        Returns:
            Optional[str]: The ID of the analysis submission
                if a new submission was made, otherwise None
                if the file already exists.

        """
        self.logger.info(f"Submitting file: {file_path}")
        try:
            if self.params.check_hash_first:
                file_stream = io.BytesIO(file_content)
                if file_manager.is_zip_file(file_obj=file_stream):
                    # Only ZIP archive type is supported for VT file upload,
                    # as endpoint decompression works only for ZIP files.
                    # Other archive types are analyzed as-is
                    # without unarchiving.
                    file_content = file_manager.extract_single_file_from_zip(
                        file=file_stream, password=password
                    )
                    file_stream = io.BytesIO(file_content)

                file_hash = file_manager.generate_file_hash(file_stream=file_stream)
                file_hash_existence = self.check_hash_existence(file_hash=file_hash)

                if self._is_report_outdated(file_hash_existence):
                    self.logger.info(f"Resubmitting file: {file_path}")
                    return self._submit_file_for_analysis(password, file_content)

                if (
                    file_hash_existence.exists_public
                    or file_hash_existence.exists_private
                ):
                    self.files_hash[file_path] = {
                        "hash": file_hash,
                        "is_private_submission": file_hash_existence.exists_private,
                    }
                    return None

            else:
                return self._submit_file_for_analysis(password, file_content)
        except GoogleThreatIntelligenceHTTPException as e:
            self.logger.exception(e)
            self._result_value = False
            raise

    def _submit_file_for_analysis(self, password: str, file_content: bytes) -> str:
        submit_url = self.api_client.get_upload_url(
            is_private_submission=self.params.private_submission
        )
        return self.api_client.submit_file_for_analysis(
            url=submit_url,
            zip_password=password,
            file_bytes=file_content,
        )

    def get_file_content(
        self, is_remote_server: bool, file_manager: FileManager, file_path: str
    ) -> bytes:
        """Retrieve the content of a file from either
        a remote server or a local source.

        Args:
             is_remote_server: Whether the file is on remote server.
             file_manager: The file manager instance used to fetch remote files.
             file_path: The path to the file.

        Return:
            bytes: The content of the file.

        """
        if is_remote_server:
            return file_manager.get_remote_unix_file_content(remote_file_path=file_path)

        return self.api_client.get_file_content(file_path=file_path)

    def _perform_action(self, _=None) -> None:
        """Main method to perform the Submit File action."""
        self.api_client.test_connectivity()
        self.params.additional_data.get("files_hashes", {})

        if self.is_first_run:
            files = (
                [file.strip() for file in self.params.files_str if file]
                if self.params.files_str
                else []
            )

            if not files and not self.params.external_urls:
                self.logger.error(ERROR_NO_ENTITIES_MESSAGE)
                raise GoogleThreatIntelligenceExceptions(ERROR_NO_ENTITIES_MESSAGE)

            is_remote_server = bool(self.params.server_address)
            file_manager = FileManager(
                address=self.params.server_address,
                username=self.params.server_username,
                password=self.params.server_password,
            )

            for external_url in self.params.external_urls:
                try:
                    file_content = self.api_client.download_file_from_url(
                        url=external_url
                    )
                    memory_file = io.BytesIO(file_content)
                    password = (
                        self.params.zip_password
                        if file_manager.is_zip_file(file_obj=memory_file)
                        else None
                    )

                    analysis_id = self.submit_file(
                        file_path=external_url,
                        file_content=file_content,
                        file_manager=file_manager,
                        password=password,
                    )
                    if analysis_id:
                        self.analysis_ids[external_url] = analysis_id
                    self.successful_files.append(external_url)
                except GoogleThreatIntelligenceHTTPException as e:
                    self.failed_entities.append(external_url)
                    self.entities_existing_data[external_url] = {
                        "execution_status": str(e)
                    }
                    self.logger.exception(e)
                    self.output_message = self._format_error_message(error=e)
                    self._result_value = False
                    raise

            for file in files:
                try:
                    file_content = self.get_file_content(
                        is_remote_server=is_remote_server,
                        file_manager=file_manager,
                        file_path=file,
                    )

                    password = self._get_zip_password(
                        file_manager=file_manager, file_path=file
                    )

                    analysis_id = self.submit_file(
                        file_path=file,
                        file_content=file_content,
                        file_manager=file_manager,
                        password=password,
                    )
                    if analysis_id:
                        self.analysis_ids[file] = analysis_id
                    self.successful_files.append(file)
                except GoogleThreatIntelligenceHTTPException as e:
                    self.failed_entities.append(file)
                    self.entities_existing_data[file] = {"execution_status": str(e)}
                    self.logger.exception(e)
                    self.output_message = self._format_error_message(error=e)
                    self._result_value = False
                    raise

            self.execution_state = ExecutionState.IN_PROGRESS
            if self.successful_files:
                self._result_value = json.dumps(
                    {
                        "analysis_ids": self.analysis_ids,
                        "files_hashes": self.files_hash,
                        "successful_files": self.successful_files,
                        "failed_entities": self.failed_entities,
                        "entities_existing_data": self.entities_existing_data,
                    }
                )

            if self.failed_entities:
                self.output_message += (
                    "The action wasn’t able to submit the "
                    "following entities using "
                    f"{SUBMIT_FILE_SCRIPT_NAME}: "
                    f"\n {', '.join(self.entities_existing_data)} \n"
                )

        if not self.is_first_run:
            analysis_ids = self.params.additional_data.get("analysis_ids")
            self.files_hash = self.params.additional_data.get("files_hashes")
            self.successful_files = self.params.additional_data.get("successful_files")
            self.failed_entities = self.params.additional_data.get("failed_entities")
            self._query_operation_status(
                task_analysis=analysis_ids,
                is_private_submission=self.params.private_submission,
            )
            if self.analysis_ids:
                self.execution_state = ExecutionState.IN_PROGRESS

                self._result_value = json.dumps(
                    {
                        "analysis_ids": self.analysis_ids,
                        "files_hashes": self.files_hash,
                        "successful_files": self.successful_files,
                        "failed_entities": self.failed_entities,
                    }
                )

            elif not self.analysis_ids and self.files_hash:
                self._finalize_action()

    def _query_operation_status(
        self, task_analysis: dict[str, str], is_private_submission: bool
    ) -> None:
        """Check the status of ongoing analysis operations.

        Args:
            task_analysis: A dictionary mapping file paths to
            a tuple containing the analysis ID and file hash.
            is_private_submission: Indicates if the analysis was submitted privately.

        Returns:
            None

        """
        for file, analysis_id in task_analysis.items():
            try:
                analysis_status, file_hash = self.api_client.check_analysis_status(
                    analysis_id,
                    show_entity_status=True,
                    is_private_submission=is_private_submission,
                    get_file_hash=True,
                )
                if analysis_status != COMPLETED:
                    self.analysis_ids[file] = analysis_id
                elif analysis_status == COMPLETED:
                    self.files_hash[file] = {
                        "hash": file_hash,
                        "is_private_submission": self.params.private_submission,
                    }
            except GoogleThreatIntelligenceHTTPException as e:
                self.entities_existing_data[file] = {"execution_status": str(e)}
                self.logger.error(
                    f"An error occurred when checking status for file {file}"
                )
                self.logger.exception(e)
        if self.analysis_ids:
            self.output_message += (
                "Waiting for action to retrieve results for "
                "the following Files: "
                f"\n{','.join(self.analysis_ids.keys())}"
            )

    def _finalize_action(self) -> None:
        """Finalizes the action by processing each file hash entry.

        Builds the final report output and updates the JSON result object.
        """
        successful_files = []
        failed_entities = self.params.additional_data.get("failed_entities")
        json_result = {}

        enricher = Enricher(api_client=self.api_client, logger=self.logger)
        ioc_type = ENTITY_TYPE_MAP.get(EntityTypes.FILEHASH)
        for ioc, entry in self.files_hash.items():
            ioc_id = entry["hash"]
            is_private_submission = entry["is_private_submission"]

            try:
                ioc_data = self.api_client.get_ioc_details(
                    ioc=ioc_id,
                    ioc_type=ioc_type,
                    is_private_submission=is_private_submission,
                )
                self.files_result_data[ioc] = ioc_data.raw_data

                should_fetch_metre_details: bool = (
                    self.params.fetch_mitre_details
                    and ioc_type == ENTITY_TYPE_MAP.get(EntityTypes.FILEHASH)
                )
                mitre_response: data_models.Mitre | None = (
                    enricher.get_mitre_response(
                        entity_identifier=ioc_id,
                        lowest_mitre_severity=self.params.lowest_mitre_severity,
                    )
                    if should_fetch_metre_details
                    else None
                )

                comments: list[data_models.Comment] | None = self._add_comments(
                    ioc=ioc,
                    ioc_id=ioc_id,
                    is_private_submission=is_private_submission,
                )
                json_result[ioc] = ioc_data.to_json_shorten(
                    comments=comments,
                    mitre_response=mitre_response,
                )

                self._add_report_link(
                    ioc=ioc, ioc_data=ioc_data, is_private=is_private_submission
                )
                is_risky: bool = assess_risk(
                    ioc_data=ioc_data,
                    gti_score=self.params.gti_score,
                    engine_threshold=self.params.engine_threshold,
                    engine_percentage_threshold=self.params.engine_percentage_threshold,
                    engine_allowlist=self.params.engine_allowlist,
                    logger=self.logger,
                )
                self.logger.info(f"is_risky={is_risky}")
                successful_files.append(ioc)
                json_result[ioc].update(
                    {
                        "is_risky": is_risky,
                        "execution_status": "success",
                    }
                )
            except GoogleThreatIntelligenceExceptions as e:
                json_result[ioc] = {"execution_status": str(e)}
                self.logger.error(
                    f"An error occurred when getting results for entity {ioc}"
                )
                self.logger.exception(e)
                failed_entities.append(ioc)

        self._summarize_results(
            successful_files=successful_files, failed_entities=failed_entities
        )

        self.json_results = convert_dict_to_json_result_dict(json_result)

    def _add_report_link(
        self, ioc: str, ioc_data: data_models.Hash, is_private: bool
    ) -> None:
        """Add report links and optionally a results table to the action result.

        Args:
            ioc: The IOC key.
            ioc_data: The IOC data object.
            is_private: Whether the submission is private.

        """
        report_link = (
            ioc_data.private_report_link if is_private else ioc_data.report_link
        )
        if not is_private:
            self.soar_action.result.add_data_table(
                title=f"Results: {ioc}",
                data_table=construct_csv(ioc_data.to_csv()),
            )
            report_link = ioc_data.report_link

        if report_link:
            self.soar_action.result.add_entity_link(ioc, report_link)

    def _add_comments(
        self,
        ioc: str,
        ioc_id: str,
        is_private_submission: bool = False,
    ) -> list[data_models.Comment] | None:
        """Optionally retrieves and logs comments if enabled in params.

        Args:
            ioc: The IOC key.
            ioc_id: The file hash.
            is_private_submission: Whether the submission is private.

        Returns:
            A list of comments if retrieved, otherwise None.

        """
        comments = None
        if self.params.retrieve_comments and is_private_submission:
            self.logger.info("Comments are not available for private submissions. Skipping comment retrieval.")
        elif self.params.retrieve_comments:
            try:
                comments = self.api_client.get_comments(
                    ioc_type=ENTITY_TYPE_MAP.get(EntityTypes.FILEHASH),
                    ioc=ioc_id,
                    limit=self.params.max_comments_to_return,
                    show_entity_status=True,
                )
                if comments:
                    self.soar_action.result.add_data_table(
                        title=f"Comments: {ioc}",
                        data_table=construct_csv(
                            [comment.to_csv() for comment in comments]
                        ),
                    )
            except GoogleThreatIntelligenceExceptions as e:
                self.logger.error(
                    f"An error occurred when retrieving comments for a {ioc}"
                )
                self.logger.exception(e)
        return comments

    def _summarize_results(
        self, successful_files: list[str], failed_entities: list[str]
    ) -> None:
        """Prepare the final output message based on success/failure results."""
        if successful_files:
            self.output_message += (
                "Successfully returned details about "
                "the following files using "
                f"{SUBMIT_FILE_SCRIPT_NAME}: \n "
                f"{', '.join(successful_files)} \n"
            )

        if failed_entities:
            self.output_message += (
                "The action wasn’t able returned details "
                "about the following files using "
                f"{SUBMIT_FILE_SCRIPT_NAME}: "
                f"\n {', '.join(failed_entities)} \n"
            )


def main() -> None:
    SubmitFile(SUBMIT_FILE_SCRIPT_NAME).run()


if __name__ == "__main__":
    main()
