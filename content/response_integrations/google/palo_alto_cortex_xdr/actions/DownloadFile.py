from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from typing import TYPE_CHECKING, Any

from SiemplifyDataModel import EntityTypes
from TIPCommon.base.action.data_models import ExecutionState
from TIPCommon.exceptions import ActionSetupError
from TIPCommon.extraction import extract_action_param
from TIPCommon.smp_time import is_approaching_action_timeout
from TIPCommon.transformation import string_to_multi_value
from TIPCommon.utils import get_entity_original_identifier

from ..core.base_action import BaseAction
from ..core import constants
from ..core.exceptions import (
    XDRAlreadyExistsException,
    XDRException,
    XDRNotFoundException,
    XDRPermissionException,
)

if TYPE_CHECKING:
    from typing import NoReturn
    from SiemplifyDataModel import DomainEntityInfo
    from TIPCommon.types import SingleJson
    from datamodels import Endpoint, FileRetrievalAction, FileRetrievalDetails


SUPPORTED_ENTITY_TYPES: list[EntityTypes] = [EntityTypes.ADDRESS, EntityTypes.HOSTNAME]


@dataclass(slots=True)
class ActionData:
    """
    Data class for holding action state across asynchronous runs.
    Key: "endpoint_id:file_path"
    Value: {
        "endpoint_id": endpoint_id,
        "file_path": file_path,
        "group_id": group_id,
        "status": status,
        "identifier": identifier
    }
    """
    endpoints_data: SingleJson | None = None
    not_found: list[str] | None = None


@dataclass(slots=True)
class FinishedRetrievalContext:
    """
    Data class for holding finished file retrieval context.
    """
    key: str
    data: SingleJson
    endpoint_id: str
    file_path: str
    group_id: str
    identifier: str
    endpoint_status: str


class DownloadFileAction(BaseAction):
    def __init__(self) -> None:
        super().__init__(constants.DOWNLOAD_FILE_SCRIPT_NAME)

    def _extract_action_parameters(self) -> None:
        self.params.incident_id = extract_action_param(
            self.soar_action,
            param_name="Incident ID",
            print_value=True,
        )
        self.params.download_folder_path = extract_action_param(
            self.soar_action,
            param_name="Download Folder Path",
            is_mandatory=True,
            print_value=True,
            default_value="/tmp",
        )
        self.params.overwrite = extract_action_param(
            self.soar_action,
            param_name="Overwrite",
            is_mandatory=True,
            print_value=True,
            default_value=False,
            input_type=bool,
        )
        file_paths_str = extract_action_param(
            self.soar_action,
            param_name="File Paths",
            is_mandatory=True,
            print_value=True,
        )
        self.params.file_paths = string_to_multi_value(
            string_value=file_paths_str,
            only_unique=True,
        )
        agent_ids_str = extract_action_param(
            self.soar_action,
            param_name="Agent ID",
            print_value=True,
            default_value="",
        )
        self.params.agent_ids = string_to_multi_value(
            string_value=agent_ids_str,
            only_unique=True,
        )
        self.params.additional_data = extract_action_param(
            self.soar_action,
            param_name="additional_data",
            default_value="{}",
        )

    def _validate_params(self) -> None:
        if not os.path.exists(self.params.download_folder_path):
            raise ActionSetupError(
                f"Folder path: {self.params.download_folder_path} does not exist."
            )
        if not os.path.isdir(self.params.download_folder_path):
            raise ActionSetupError(
                f"Folder path: {self.params.download_folder_path} is not a directory."
            )

    def _perform_action(self, _) -> None:
        self._set_action_data()

        if not self.action_data.endpoints_data:
            suitable_entities: list[DomainEntityInfo] = [
                entity
                for entity in self.soar_action.target_entities
                if entity.entity_type
                and entity.entity_type.upper() in SUPPORTED_ENTITY_TYPES
            ]

            if not suitable_entities and not self.params.agent_ids:
                self.output_message = (
                    "No suitable entities or agent IDs were provided to download file "
                    "from."
                )
                self.result_value = False
                return

            self._start_file_retrieval(suitable_entities)
        else:
            self._query_retrieval_status()

    def _set_action_data(self) -> None:
        self.action_data = (
            ActionData(**json.loads(self.params.additional_data))
            if self.params.additional_data and self.params.additional_data != "{}"
            else ActionData(endpoints_data={}, not_found=[])
        )

    def _start_file_retrieval(self, suitable_entities: list[DomainEntityInfo]) -> None:
        total_provided_identifiers: int = len(suitable_entities) + len(
            self.params.agent_ids
        )
        resolved_endpoints: SingleJson = self._resolve_all_endpoints(suitable_entities)

        if not resolved_endpoints:
            self._finish_operation(total_provided_identifiers)
            return

        if not self.params.overwrite:
            self._pre_validate_overwrite_conflicts(resolved_endpoints)

        self._initiate_retrievals(resolved_endpoints)

        if self._get_pending_keys():
            self._set_action_in_progress()
        else:
            self._finish_operation(total_provided_identifiers)

    def _resolve_all_endpoints(
        self,
        suitable_entities: list[DomainEntityInfo],
    ) -> SingleJson:
        resolved_endpoints: SingleJson = {}
        self._resolve_suitable_entities(suitable_entities, resolved_endpoints)
        self._resolve_agent_ids(resolved_endpoints)

        return resolved_endpoints

    def _resolve_suitable_entities(
        self,
        suitable_entities: list[DomainEntityInfo],
        resolved_endpoints: SingleJson,
    ) -> None:
        for entity in suitable_entities:
            entity_identifier: str = get_entity_original_identifier(entity)
            try:
                endpoint: Endpoint = self._get_endpoint(entity, entity_identifier)
                os_type: str = self._map_os_type(endpoint.os_type)
                resolved_endpoints[endpoint.endpoint_id] = {
                    "identifier": entity_identifier,
                    "os_type": os_type,
                }
                self.logger.info(
                    f"Resolved entity {entity_identifier} to endpoint "
                    f"{endpoint.endpoint_id} with OS {os_type}"
                )
            except XDRNotFoundException:
                self.logger.info(
                    f"Endpoint for entity {entity_identifier} was not found. Skipping.."
                )
                self.action_data.not_found.append(entity_identifier)
            except XDRException as e:
                self.logger.error(
                    f"An error occurred on entity {entity_identifier}: {e}"
                )
                self.logger.exception(e)
                self.action_data.not_found.append(entity_identifier)

    def _resolve_agent_ids(self, resolved_endpoints: SingleJson) -> None:
        for agent_id in self.params.agent_ids:
            if agent_id in resolved_endpoints:
                self.logger.info(
                    f"Agent ID/Identifier {agent_id} already resolved from entity. "
                    "Skipping."
                )
                continue

            try:
                endpoint: Endpoint = self._get_endpoint_by_identifier(agent_id)
                os_type: str = self._map_os_type(endpoint.os_type)
                resolved_endpoints[endpoint.endpoint_id] = {
                    "identifier": agent_id,
                    "os_type": os_type,
                }
                self.logger.info(
                    f"Resolved Agent ID/Identifier {agent_id} to endpoint "
                    f"{endpoint.endpoint_id} with OS {os_type}"
                )
            except XDRNotFoundException:
                self.logger.info(
                    f"Endpoint for Agent ID/Identifier {agent_id} was not found. "
                    "Skipping..."
                )
                self.action_data.not_found.append(agent_id)
            except XDRException as e:
                self.logger.error(
                    f"An error occurred on Agent ID/Identifier {agent_id}: {e}"
                )
                self.logger.exception(e)
                self.action_data.not_found.append(agent_id)

    def _pre_validate_overwrite_conflicts(self, resolved_endpoints: SingleJson) -> None:
        for info in resolved_endpoints.values():
            identifier: str = info[constants.IDENTIFIER_KEY]
            for file_path in self.params.file_paths:
                filename: str = self._normalize_filename(identifier, file_path)
                dest_path: str = os.path.join(
                    self.params.download_folder_path, filename
                )
                if os.path.exists(dest_path):
                    raise XDRAlreadyExistsException(
                        f"files with path {dest_path} already exist. Please delete the "
                        "files or set 'Overwrite' to true."
                    )

    def _initiate_retrievals(self, resolved_endpoints: SingleJson) -> None:
        for endpoint_id, info in resolved_endpoints.items():
            self._initiate_retrievals_for_endpoint(
                endpoint_id, info[constants.IDENTIFIER_KEY], info[constants.OS_TYPE_KEY]
            )

    def _initiate_retrievals_for_endpoint(
        self, endpoint_id: str, identifier: str, os_type: str
    ) -> None:
        for file_path in self.params.file_paths:
            self._trigger_file_retrieval_api(
                endpoint_id, file_path, os_type, identifier
            )

    def _trigger_file_retrieval_api(
        self, endpoint_id: str, file_path: str, os_type: str, identifier: str
    ) -> None:
        compound_key: str = f"{endpoint_id}:{file_path}"
        try:
            self.logger.info(
                f"Initiating file retrieval for endpoint {endpoint_id}, file path "
                f"{file_path}..."
            )
            file_retrieval_action: FileRetrievalAction
            file_retrieval_action = self.api_client.retrieve_file_from_endpoint(
                endpoint_id=endpoint_id,
                os_type=os_type,
                file_paths=[file_path],
                incident_id=self.params.incident_id,
            )
            action_id: Any = file_retrieval_action.action_id
            if not action_id:
                raise XDRException(
                    f"No action_id returned by XDR for endpoint {endpoint_id}"
                )

            self.action_data.endpoints_data[compound_key] = {
                constants.ENDPOINT_ID_KEY: endpoint_id,
                constants.FILE_PATH_KEY: file_path,
                constants.GROUP_ID_KEY: str(action_id),
                constants.STATUS_KEY: constants.PENDING_STATUS,
                constants.IDENTIFIER_KEY: identifier,
            }
            self.logger.info(
                f"Retrieval initiated. Action ID: {action_id} for key {compound_key}."
            )
        except XDRPermissionException:
            raise
        except Exception as e:
            self.logger.error(
                f"Failed to initiate file retrieval for {compound_key}: {e}"
            )
            self.logger.exception(e)
            self.action_data.endpoints_data[compound_key] = {
                constants.ENDPOINT_ID_KEY: endpoint_id,
                constants.FILE_PATH_KEY: file_path,
                constants.GROUP_ID_KEY: "",
                constants.STATUS_KEY: "Failed",
                constants.IDENTIFIER_KEY: identifier,
            }

    def _get_endpoint(
        self, entity: DomainEntityInfo, entity_identifier: str
    ) -> Endpoint:
        if entity.entity_type and entity.entity_type.upper() == EntityTypes.ADDRESS:
            return self.api_client.get_endpoint_by_ip(entity_identifier)
        return self.api_client.get_endpoint_by_hostname(entity_identifier)

    def _is_valid_agent_id(self, agent_id: str) -> bool:
        return bool(constants.AGENT_ID_VALIDATION_REGEX.fullmatch(agent_id))

    def _get_endpoint_by_identifier(self, identifier: str) -> Endpoint:
        if self._is_valid_agent_id(identifier):
            return self.api_client.get_endpoint_by_id(identifier)

        try:
            return self.api_client.get_endpoint_by_ip(identifier)
        except XDRNotFoundException:
            return self.api_client.get_endpoint_by_hostname(identifier)

    def _map_os_type(self, raw_os_type: str) -> str:
        if not raw_os_type:
            return constants.WINDOWS_OS_TYPE
        os_lower = raw_os_type.lower()
        if "windows" in os_lower:
            return constants.WINDOWS_OS_TYPE
        if "linux" in os_lower:
            return constants.LINUX_OS_TYPE
        if "mac" in os_lower or "osx" in os_lower or "macos" in os_lower:
            return constants.MACOS_OS_TYPE
        return constants.WINDOWS_OS_TYPE

    def _query_retrieval_status(self) -> None:
        self._validate_timeout()

        pending_keys: list[str] = self._get_pending_keys()
        for key in pending_keys:
            data: SingleJson = self.action_data.endpoints_data[key]
            try:
                self._retrieve_and_download_file(key, data)
            except (XDRAlreadyExistsException, XDRPermissionException):
                raise
            except Exception as e:
                self.logger.error(
                    f"Error checking status/downloading file for key {key}: {e}"
                )
                self.logger.exception(e)
                data[constants.STATUS_KEY] = "FAILED"

        resolved_endpoints: set[str] = {
            data[constants.ENDPOINT_ID_KEY]
            for data in self.action_data.endpoints_data.values()
        }
        total_provided_identifiers: int = len(resolved_endpoints) + len(
            self.action_data.not_found
        )

        if self._get_pending_keys():
            self._set_action_in_progress()
        else:
            self._finish_operation(total_provided_identifiers)

    def _retrieve_and_download_file(self, key: str, data: SingleJson) -> None:
        endpoint_id: str = data[constants.ENDPOINT_ID_KEY]
        file_path: str = data[constants.FILE_PATH_KEY]
        group_id: str = data[constants.GROUP_ID_KEY]
        identifier: str = data[constants.IDENTIFIER_KEY]

        action_status: SingleJson = (
            self.api_client.get_action_status(action_id=int(group_id)) or {}
        )
        endpoint_status: str = action_status.get("data", {}).get(
            endpoint_id, constants.PENDING_STATUS
        )
        self.logger.info(
            f"Status for key {key} under action {group_id}: {endpoint_status}"
        )

        data[constants.STATUS_KEY] = endpoint_status

        if endpoint_status in constants.FINISHED_STATUSES:
            context = FinishedRetrievalContext(
                key=key,
                data=data,
                endpoint_id=endpoint_id,
                file_path=file_path,
                group_id=group_id,
                identifier=identifier,
                endpoint_status=endpoint_status,
            )
            self._handle_finished_file_retrieval(context)

    def _handle_finished_file_retrieval(
        self,
        context: FinishedRetrievalContext,
    ) -> None:
        if context.endpoint_status == constants.SUCCESS_STATUS:
            self.logger.info(
                f"File retrieval completed for key {context.key}. Requesting download.."
            )
            details: FileRetrievalDetails = self.api_client.get_file_retrieval_details(
                group_id=context.group_id
            )
            download_url: str = details.endpoint_url_map.get(context.endpoint_id)
            if not download_url:
                raise XDRException(
                    f"No download URL found for endpoint {context.endpoint_id} in "
                    f"action {context.group_id}"
                )

            filename: str = self._normalize_filename(
                context.identifier, context.file_path
            )
            dest_path: str = os.path.join(self.params.download_folder_path, filename)

            if not os.path.exists(self.params.download_folder_path):
                os.makedirs(self.params.download_folder_path)

            if not self.params.overwrite and os.path.exists(dest_path):
                raise XDRAlreadyExistsException(
                    f"files with path {dest_path} already exist. Please delete the "
                    "files or set 'Overwrite' to true."
                )

            self._save_downloaded_content(download_url, dest_path)
            context.data[constants.LOCAL_PATH_KEY] = dest_path
        else:
            self.logger.error(
                f"File retrieval failed/aborted for key {context.key}. Status:"
                f"{context.endpoint_status}"
            )

    def _save_downloaded_content(self, download_url: str, dest_path: str) -> None:
        with self.api_client.retrieve_file(download_url=download_url) as response:
            with open(dest_path, "wb") as file_obj:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        file_obj.write(chunk)
        self.logger.info(f"File successfully written to: {dest_path}")

    def _normalize_filename(self, identifier: str, file_path: str) -> str:
        safe_path: str = (
            file_path.strip().replace(":", "_").replace("\\", "_").replace("/", "_")
        )
        safe_path = safe_path.strip("_")
        while "__" in safe_path:
            safe_path = safe_path.replace("__", "_")
        return f"{identifier}-{safe_path}.zip"

    def _get_pending_keys(self) -> list[str]:
        return [
            key
            for key, data in self.action_data.endpoints_data.items()
            if data[constants.STATUS_KEY] not in constants.FINISHED_STATUSES
        ]

    def _validate_timeout(self) -> None:
        if is_approaching_action_timeout(
            self.soar_action.async_total_duration_deadline
        ):
            pending_endpoints = ", ".join(
                {
                    data[constants.IDENTIFIER_KEY]
                    for data in self.action_data.endpoints_data.values()
                    if data[constants.STATUS_KEY] not in constants.FINISHED_STATUSES
                }
            )
            raise XDRException(
                f"action ran into a timeout during execution. "
                f"Pending endpoints: {pending_endpoints}. "
                f"Note: the download will be started again during the action re-run. "
                f"Please increase the timeout in IDE."
            )

    def _set_action_in_progress(self) -> None:
        pending_names = {
            data[constants.IDENTIFIER_KEY]
            for data in self.action_data.endpoints_data.values()
            if data[constants.STATUS_KEY] not in constants.FINISHED_STATUSES
        }
        self.output_message = (
            f"Waiting for file retrieval to finish on: {', '.join(pending_names)}"
        )
        self.result_value = json.dumps(asdict(self.action_data))
        self.execution_state = ExecutionState.IN_PROGRESS

    def _finish_operation(self, total_provided_identifiers: int) -> None:
        results_by_identifier: SingleJson = self._group_results_by_identifier()

        self.json_results = [
            {
                "Entity": identifier,
                "EntityResult": {
                    "download_file_path": info[constants.DOWNLOAD_FILE_PATH_KEY],
                    "errored_file_paths": info[constants.ERRORED_FILE_PATHS_KEY],
                },
            }
            for identifier, info in results_by_identifier.items()
        ]

        self.output_message = self._generate_output_message(
            results_by_identifier, total_provided_identifiers
        )
        self.result_value = any(
            len(info["download_file_path"]) > constants.NULL_VALUE
            for info in results_by_identifier.values()
        )
        self.execution_state = ExecutionState.COMPLETED

    def _group_results_by_identifier(self) -> SingleJson:
        results_by_identifier: SingleJson = {}
        for data in self.action_data.endpoints_data.values():
            identifier: str = data[constants.IDENTIFIER_KEY]
            if identifier not in results_by_identifier:
                results_by_identifier[identifier] = {
                    "download_file_path": [],
                    "errored_file_paths": [],
                }

            if (
                data[constants.STATUS_KEY] == constants.SUCCESS_STATUS
                and constants.LOCAL_PATH_KEY in data
            ):
                results_by_identifier[identifier][
                    constants.DOWNLOAD_FILE_PATH_KEY
                ].append(data[constants.LOCAL_PATH_KEY])
            else:
                results_by_identifier[identifier][
                    constants.ERRORED_FILE_PATHS_KEY
                ].append(data[constants.FILE_PATH_KEY])

        return results_by_identifier

    def _generate_output_message(
        self,
        results_by_identifier: SingleJson,
        total_provided_identifiers: int,
    ) -> str:
        completed_endpoints, partial_endpoints, failed_endpoints = (
            self._classify_endpoint_results(results_by_identifier)
        )
        not_found_endpoints: list[str] = self.action_data.not_found

        messages: list[str] = self._compile_endpoint_messages(
            completed_endpoints,
            partial_endpoints,
            failed_endpoints,
            not_found_endpoints,
        )

        output_message: str = "\n".join(messages)

        if (
            len(not_found_endpoints) == total_provided_identifiers
            and total_provided_identifiers > constants.NULL_VALUE
        ):
            output_message = (
                "None of the provided endpoints were found in Palo Alto XDR."
            )
        elif not output_message:
            output_message = "No endpoints were processed."

        return output_message

    def _classify_endpoint_results(
        self, results_by_identifier: SingleJson
    ) -> tuple[list[str], list[str], list[str]]:
        completed_endpoints: list[str] = []
        partial_endpoints: list[str] = []
        failed_endpoints: list[str] = []

        for identifier, info in results_by_identifier.items():
            downloaded: int = len(info[constants.DOWNLOAD_FILE_PATH_KEY])
            errored: int = len(info[constants.ERRORED_FILE_PATHS_KEY])

            if downloaded > constants.NULL_VALUE and errored == constants.NULL_VALUE:
                completed_endpoints.append(identifier)
            elif downloaded > constants.NULL_VALUE and errored > constants.NULL_VALUE:
                partial_endpoints.append(identifier)
            else:
                failed_endpoints.append(identifier)

        return completed_endpoints, partial_endpoints, failed_endpoints

    def _compile_endpoint_messages(
        self,
        completed: list[str],
        partial: list[str],
        failed: list[str],
        not_found: list[str],
    ) -> list[str]:
        messages: list[str] = []
        if completed:
            messages.append(
                "Successfully downloaded files from the following endpoints in Palo"
                f" Alto XDR: {', '.join(completed)}."
            )
        if partial:
            messages.append(
                "Not all files were downloaded for the following endpoints in Palo "
                f"Alto XDR: {', '.join(partial)}. Please check JSON Result for more "
                "information."
            )
        if failed:
            messages.append(
                "Failed to retrieve files from the following endpoints in Palo Alto "
                f"XDR: {', '.join(failed)}."
            )
        if not_found:
            messages.append(
                "The following endpoints weren’t found in Palo Alto XDR: "
                f"{', '.join(not_found)}"
            )
        return messages


def main() -> NoReturn:
    DownloadFileAction().run()


if __name__ == "__main__":
    main()
