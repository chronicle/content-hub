# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import annotations

from typing import NoReturn
import dataclasses
import json

from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyDataModel import DomainEntityInfo, EntityTypes
from soar_sdk.SiemplifyLogger import SiemplifyLogger
from soar_sdk.SiemplifyUtils import output_handler

from TIPCommon.base.action.data_models import ExecutionState
from TIPCommon.extraction import extract_action_param
from TIPCommon.transformation import convert_dict_to_json_result_dict
from TIPCommon.types import SingleJson
from TIPCommon.utils import is_empty_string_or_none
from TIPCommon.validation import ParameterValidator

from crowd_strike_falcon.core.AsyncActionBaseClass import ActionResult, AsyncActionBaseClass
from crowd_strike_falcon.core.CrowdStrikeManager import CrowdStrikeManager
from crowd_strike_falcon.core.CrowdStrikeParser import CrowdStrikeParser
from crowd_strike_falcon.core import constants
from crowd_strike_falcon.core import datamodels
from crowd_strike_falcon.core import exceptions
from crowd_strike_falcon.core.utils import get_entity_original_identifier, is_unicode_string, validate_device_id


INTEGRATION_NAME = constants.INTEGRATION_NAME
ENTITIES_DELIMITER = "\n"


@dataclasses.dataclass
class ActionData:
    in_progress: dict[str, str]
    completed: SingleJson
    failed_script_execution: list[str]
    data_not_available: list[str]
    not_found: list[str]
    not_accessible_entities: list[str]
    offline_queued: list[str]
    offline_queued_with_results: list[dict]

    @classmethod
    def from_json(cls, action_data: SingleJson) -> ActionData:
        return cls(
            in_progress=action_data["in_progress"],
            completed=action_data["completed"],
            failed_script_execution=action_data["failed_script_execution"],
            data_not_available=action_data["data_not_available"],
            not_found=action_data["not_found"],
            not_accessible_entities=action_data["not_accessible_entities"],
            offline_queued=action_data.get("offline_queued", []),
            offline_queued_with_results=action_data.get(
                "offline_queued_with_results", []
            ),
        )


class RunScriptAction(AsyncActionBaseClass):
    def __init__(self, siemplify):
        super().__init__(siemplify)
        self.parser = CrowdStrikeParser()
        self.results = ActionData(
            in_progress={},
            completed={},
            failed_script_execution=[],
            data_not_available=[],
            not_found=[],
            not_accessible_entities=[],
            offline_queued=[],
            offline_queued_with_results=[],
        )
        self.admin_command = True
        self.action_msg = ActionMessages(data=self.results, logger=self.logger)

    def _extract_action_configuration(self):
        integration_cid = self.config.customer_id
        action_cid = extract_action_param(
            siemplify=self.siemplify,
            param_name="Customer ID",
            print_value=True,
        )

        customer_id = action_cid or integration_cid
        self.params.customer_id = customer_id

        if self.params.customer_id:
            self.config.customer_id = self.params.customer_id

        self.params.script_name = extract_action_param(
            siemplify=self.siemplify, param_name="Script Name", print_value=True
        )
        self.params.raw_script = extract_action_param(
            siemplify=self.siemplify, param_name="Raw Script", print_value=True
        )
        self.params.hostname = extract_action_param(
            siemplify=self.siemplify, param_name="Hostname", print_value=True
        )
        self.params.device_id = extract_action_param(
            siemplify=self.siemplify, param_name="Device ID", print_value=True
        )
        validate_device_id(self.params.device_id)
        self.params.additional_data = extract_action_param(
            siemplify=self.siemplify, param_name="additional_data", default_value="{}"
        )
        self.params.queue_offline = extract_action_param(
            siemplify=self.siemplify,
            param_name="Queue Offline",
            input_type=bool,
            is_mandatory=False,
            print_value=True,
            default_value=False,
        )

    def _validate_params(self, validator: ParameterValidator) -> None:
        _ = validator
        if is_empty_string_or_none(self.params.script_name) and is_empty_string_or_none(
            self.params.raw_script
        ):
            raise exceptions.CrowdStrikeFalconValidatorException(
                self.action_msg.action_param_error_msg()
            )

        self.params.additional_data = validator.validate_json(
            param_name="additional_data",
            json_string=self.params.additional_data,
            default_value="{}",
            print_value=False,
        )

        self.params.hostnames = validator.validate_csv(
            param_name="Hostname",
            csv_string=self.params.hostname,
        )
        self.params.device_ids = validator.validate_csv(
            param_name="Device ID",
            csv_string=self.params.device_id,
        )

    def _perform_action(self, manager: CrowdStrikeManager) -> tuple[int, bool]:
        self._set_action_data()
        if not self.results.in_progress:
            self._run_script_on_entities(manager=manager)
        self._get_entities_status(manager=manager)
        self._log_messages()
        self._set_json_result()

        return self._finalize_action()

    def _set_action_data(self) -> None:
        if self.params.additional_data:
            self.results = ActionData.from_json(self.params.additional_data)
            self.action_msg = ActionMessages(data=self.results, logger=self.logger)

    def _run_script_on_entities(self, manager: CrowdStrikeManager) -> None:
        """Get entity device status from CrowdStrike and execute the script or script
        payload once session created.

        Args:
            manager (CrowdStrikeManager): CrowdStrikeManager instance.
        """
        supported_entities = self._get_supported_entities()
        seen_devices = {}
        for entity_identifier, entity_type in supported_entities.items():
            self.logger.info(f"Processing entity {entity_identifier}.")
            devices = self._search_entity_devices(
                manager, entity_identifier, entity_type
            )
            if not devices:
                self.logger.info(f"Entity {entity_identifier} doesn't found.")
                self.results.not_found.append(entity_identifier)
                continue

            if devices[0] in seen_devices:
                self.logger.info(
                    f"Identifier '{entity_identifier}' maps to device ID '{devices[0]}', which is already "
                    f"associated with entity '{seen_devices[devices[0]]}'. Skipping duplication."
                )
                continue

            seen_devices[devices[0]] = entity_identifier

            if len(devices) > 1:
                self.action_msg.log_multiple_entries(entity_identifier)

            self._process_entity_device(manager, entity_identifier, devices)

    def _get_supported_entities(self) -> dict[str, str]:
        supported_entities = [
            entity
            for entity in self.siemplify.target_entities
            if entity.entity_type in constants.ENTITIES_MAPPER
        ]

        if not supported_entities and not self.params.hostnames and not self.params.device_ids:
            raise exceptions.CrowdStrikeError(
                "Action failed to run as there were no matching entities provided, "
                "and no value provided in the \"Hostname\" or \"Device ID\" parameters."
            )

        supported_items_mapping = {
            get_entity_original_identifier(entity): entity.entity_type
            for entity in supported_entities
        }
        supported_items_mapping.update({
            hostname: EntityTypes.HOSTNAME
            for hostname in self.params.hostnames
        })
        supported_items_mapping.update({
            device_id: "DEVICE_ID"
            for device_id in self.params.device_ids
        })

        return supported_items_mapping

    def _search_entity_devices(
        self, manager: CrowdStrikeManager, entity_identifier: str, entity_type: str
    ) -> list[str]:
        if entity_type == "DEVICE_ID":
            device_info = manager.get_devices(devices_ids=[entity_identifier])
            return [entity_identifier] if device_info else []

        request_filter = {
            key: entity_identifier for key in constants.ENTITIES_MAPPER[entity_type]
        }
        request_filter["cid"] = self.params.customer_id

        try:
            return manager.search_device_ids(**request_filter)

        except exceptions.CrowdStrikeBadRequestError as err:
            is_unicode_cid = is_unicode_string(self.params.customer_id)
            if constants.CID_ERROR in str(err).lower() or is_unicode_cid:
                raise exceptions.InvalidCidError(
                    "Incorrect Customer ID specified."
                ) from err

        return []

    def _process_entity_device(
        self, manager: CrowdStrikeManager, entity_identifier: str, devices: list[str]
    ) -> bool:
        try:
            devices_info = manager.get_devices(devices_ids=devices)
            if not devices_info:
                self.results.not_found.append(entity_identifier)
                return False

            self.logger.info(f"Device details found for entity {entity_identifier}.")
            online_device = self._get_online_device(
                manager=manager,
                entity_identifier=entity_identifier,
                devices_info=devices_info,
            )

            if not online_device:
                return self._handle_offline_or_inaccessible(
                    manager, entity_identifier, devices_info
                )

            session_id = self._create_entity_device_session(
                manager=manager,
                entity_identifier=entity_identifier,
                device_id=devices[0],
            )
            if not session_id:
                return False

            return self._execute_script(
                manager=manager,
                entity_identifier=entity_identifier,
                device_id=devices[0],
                session_id=session_id,
            )

        except exceptions.CrowdStrikeSessionCreatedError as e:
            self._handle_session_error(entity_identifier, e)
            return False

    def _get_online_device(
        self,
        manager: CrowdStrikeManager,
        entity_identifier: str,
        devices_info: list[datamodels.Device],
    ) -> datamodels.Device | None:
        """
        Get the first online and normally-functioning device from a list of devices.
        """
        self.logger.info(f"Getting online device for entity: {entity_identifier}.")
        online_states = manager.get_devices_online_states(
            [d.device_id for d in devices_info]
        )
        for device_info in devices_info:
            device_info.online_state = next(
                (
                    state
                    for state in online_states
                    if state.device_id == device_info.device_id
                ),
                None,
            )

        online_device = next(
            (
                device
                for device in devices_info
                if device.status == constants.STATUS_NORMAL
                and device.online_state
                and device.online_state.state == constants.STATE_ONLINE
            ),
            None,
        )
        return online_device

    def _handle_offline_or_inaccessible(
        self,
        manager: CrowdStrikeManager,
        entity_identifier: str,
        devices_info: list[datamodels.Device],
    ) -> bool:
        """
        Handle devices that are not online.
        Queue for offline execution or mark as inaccessible.
        """
        offline_device = next(
            (
                device for device in devices_info
                if device.status == constants.STATUS_NORMAL
                and device.online_state
                and device.online_state.state == constants.STATE_OFFLINE
            ),
            None,
        )

        if offline_device and self.params.queue_offline:
            self.logger.info(
                f"Device for {entity_identifier} is offline. Queuing script."
            )
            session_id = self._create_entity_device_session(
                manager, entity_identifier, offline_device.device_id
            )
            if not session_id:
                return False

            cloud_request_id = self._execute_script(
                manager,
                entity_identifier,
                offline_device.device_id,
                session_id,
                is_offline=True,
            )
            if cloud_request_id:
                self.results.offline_queued_with_results.append(
                    {
                        "entity_identifier": entity_identifier,
                        "api_response": {
                            "session_id": session_id,
                            "cloud_request_id": cloud_request_id,
                            "queued_command_offline": True,
                        },
                    }
                )
                self.results.offline_queued.append(entity_identifier)
            return True

        self.logger.info(f"Entity device {entity_identifier} is not accessible.")
        self.results.not_accessible_entities.append(entity_identifier)
        return False

    def _is_not_accessible_device(
        self, device_info: datamodels.Device, device_state: datamodels.OnlineState
    ) -> bool:
        return (
            device_info.status != constants.STATUS_NORMAL
            or device_state.state != constants.STATE_ONLINE
        )

    def _create_entity_device_session(
        self, manager: CrowdStrikeManager, entity_identifier: str, device_id: str
    ) -> str | None:
        session_id = manager.create_device_session(device_id=device_id)
        if session_id:
            self.logger.info(f"Device session created for entity {entity_identifier}.")
            return session_id

        self.logger.info(
            "Unable to get create device session id for entity {entity_identifier}."
        )
        self.results.data_not_available.append(entity_identifier)

        return None

    def _execute_script(
        self,
        manager: CrowdStrikeManager,
        entity_identifier: str,
        device_id: str,
        session_id: str,
        is_offline: bool = False,
    ) -> str | None:
        cloud_request_id = manager.execute_responder_script(
            device_id=device_id,
            session_id=session_id,
            command=(
                constants.RUN_SCRIPT_RAW_COMMAND.format(
                    raw_script=self.params.raw_script
                )
                if self.params.raw_script
                else constants.RUN_SCRIPT_COMMAND.format(
                    script_name=self.params.script_name
                )
            ),
        )
        if not cloud_request_id:
            self.results.failed_script_execution.append(entity_identifier)
            return None

        if not is_offline:
            self.logger.info(
                f"Script {self.params.raw_script or self.params.script_name} has been "
                f"executed on device entity {entity_identifier}."
            )
            self.results.in_progress[entity_identifier] = cloud_request_id

        return cloud_request_id

    def _handle_session_error(self, entity_identifier: str, e: Exception) -> None:
        self.results.data_not_available.append(entity_identifier)
        self.logger.error(f"An error occurred on entity {entity_identifier}")
        self.logger.exception(e)

    def _get_entities_status(self, manager: CrowdStrikeManager) -> None:
        in_progress_items = self.results.in_progress.copy()

        for entity_identifier, cloud_request_id in in_progress_items.items():
            if entity_identifier in self.results.offline_queued:
                continue

            try:
                script_status = manager.get_status_of_responder_command(
                    cloud_request_id=cloud_request_id, admin_command=self.admin_command
                )
                if script_status and script_status[0].complete:
                    self.logger.info(
                        f"{self.params.raw_script or self.params.script_name} has been "
                        f"executed on entity device {entity_identifier}."
                    )
                    self.results.completed[entity_identifier] = script_status[
                        0
                    ].to_json()
                    self.results.in_progress.pop(entity_identifier)

            except exceptions.CrowdStrikeSessionCreatedError as e:
                self._handle_session_error(entity_identifier, e)

        for entity_identifier in self.results.offline_queued:
            if entity_identifier in self.results.in_progress:
                self.results.in_progress.pop(entity_identifier)

    def _log_messages(self) -> None:
        self.action_msg.log_messages(self.params.script_name, self.params.raw_script)

    def _set_json_result(self) -> None:
        json_results = self.results.completed.copy()

        if not self.results.in_progress and self.results.offline_queued_with_results:
            for item in self.results.offline_queued_with_results:
                json_results[item["entity_identifier"]] = item["api_response"]

        if json_results:
            self.siemplify.result.add_result_json(
                convert_dict_to_json_result_dict(json_results)
            )

    def _finalize_action(self) -> ActionResult:
        if self._is_timeout():
            return self._finalize_action_on_timeout()

        if self.results.in_progress:
            return self._finalize_action_on_inprogress()

        if not self.results.completed and not self.results.offline_queued:
            return self._finalize_action_on_failure()

        return self._finalize_action_on_success()

    def _finalize_action_on_timeout(self) -> ActionResult:
        if self.results.completed:
            self.output_messages.append(
                self.action_msg.timeout_with_success_msg(
                    script_name=self.params.script_name,
                    script_payload=self.params.raw_script,
                )
            )
            if self._get_failed_entities_as_list():
                return ActionResult(ExecutionState.TIMED_OUT, False)

            return ActionResult(ExecutionState.TIMED_OUT, True)

        self.output_messages.append(self.action_msg.timeout_with_failure_msg())

        return ActionResult(ExecutionState.FAILED, False)

    def _finalize_action_on_inprogress(self) -> ActionResult:
        self.output_messages.append(self.action_msg.in_progress_msg())
        return ActionResult(
            ExecutionState.IN_PROGRESS, json.dumps(dataclasses.asdict(self.results))
        )

    def _finalize_action_on_failure(self) -> ActionResult:
        msg = self.action_msg.failed_entities_output_msg(
            script_name=self.params.script_name, script_payload=self.params.raw_script
        )
        self.output_messages.append(msg)
        return ActionResult(ExecutionState.COMPLETED, False)

    def _finalize_action_on_success(self) -> ActionResult:
        msg = self.action_msg.success_entities_output_msg(
            script_name=self.params.script_name, script_payload=self.params.raw_script
        )
        self.output_messages.append(msg)
        if self._get_failed_entities_as_list():
            return ActionResult(ExecutionState.COMPLETED, False)

        return ActionResult(ExecutionState.COMPLETED, True)

    def _get_failed_entities_as_list(self) -> list[str]:
        return (
            self.results.failed_script_execution
            + self.results.data_not_available
            + self.results.not_found
            + self.results.not_accessible_entities
        )


@dataclasses.dataclass
class ActionMessages:
    data: ActionData
    logger: SiemplifyLogger

    def log_messages(self, script_name: str, script_payload: str) -> None:
        """Log output messages.

        Args:
            script_name (str): Script name provided in action parameter.
            script_payload (str): Script payload provided in action parameter.
        """
        if self.data.completed:
            self.logger.info(
                self.success_entities_output_msg(script_name, script_payload)
            )

    def log_multiple_entries(self, entity_identifier: str) -> None:
        self.logger.info(
            f"Multiple entries were found for entity: {entity_identifier}. "
            "First one is taken"
        )

    def success_entities_output_msg(self, script_name: str, script_payload: str) -> str:
        """Output message for success entities to execute script.

        Args:
            script_name (str): Script name provided in action parameter.
            script_payload (str): Script payload provided in action parameter.

        Returns:
            str: output message.
        """
        script_payload = "raw script" if script_payload else ""
        msg_chunk = "provided raw script" if script_payload else f"script {script_name}"

        if not self.data.completed and self.data.offline_queued:
            offline_entities_str = ENTITIES_DELIMITER.join(self.data.offline_queued)
            msg =  (
                "Command has been queued for the following offline endpoints in "
                f"{INTEGRATION_NAME}:"
                f"\n{offline_entities_str}"
            )
            msg += f"\n{self.failed_entities_output_msg(script_name, script_payload)}"
            return msg.strip()

        if not self.data.completed:
            return ""

        entities = ENTITIES_DELIMITER.join(sorted(list(self.data.completed.keys())))
        msg = (
            f"Successfully executed {msg_chunk} on "
            f"the following endpoints in {INTEGRATION_NAME}:\n{entities}."
        )

        if self.data.offline_queued:
            offline_entities_str = ENTITIES_DELIMITER.join(self.data.offline_queued)
            msg += (
                "\nCommand has been queued for the following offline endpoints in "
                f"{INTEGRATION_NAME}:"
                f"\n{offline_entities_str}"
            )

        msg += f"\n{self.failed_entities_output_msg(script_name, script_payload)}"

        return msg.strip()

    def failed_entities_output_msg(self, script_name: str, script_payload: str) -> str:
        """Output message for failed entities to execute script.

        Args:
            script_name (str): Script name provided in action parameter.
            script_payload (str): Script payload provided in action parameter.

        Returns:
            str: output message.
        """
        script_payload = "raw script" if script_payload else ""
        msg_chunk = "provided raw script" if script_payload else f"script {script_name}"
        failed_entities = set(
            self.data.failed_script_execution
            + self.data.data_not_available
            + self.data.not_found
            + self.data.not_accessible_entities
        ) - set(self.data.offline_queued or [])
        if not self.data.completed and not self.data.offline_queued:
            return (
                "Script wasn't executed on the provided endpoints in "
                f"{INTEGRATION_NAME}."
            )

        if not failed_entities:
            return ""

        failed_entities_str = ENTITIES_DELIMITER.join(sorted(list(failed_entities)))
        return (
            f"Action wasn't able to execute {msg_chunk} on "
            f"the following endpoints in {INTEGRATION_NAME}:\n{failed_entities_str}."
        )

    def in_progress_msg(self) -> str:
        entities = ENTITIES_DELIMITER.join(self.data.in_progress)
        return (
            "Waiting for the scripts to finish execution on the following endpoints:\n"
            f"{entities}"
        )

    def action_param_error_msg(self) -> str:
        return 'either "Script Name" or "Raw Script" should be provided.'

    def timeout_with_success_msg(self, script_name: str, script_payload: str) -> str:
        """Timeout output message timeout.

        Args:
            script_name (str): Script name provided in action parameter.
            script_payload (str): Script payload provided in action parameter.

        Returns:
            str: output message.
        """
        timeout_msg = (
            "Action ran into a timeout during execution. "
            "Please increase the timeout in IDE."
        )
        msg = (
            f"{self.success_entities_output_msg(script_name, script_payload)}\n"
            f"{timeout_msg}"
        )

        return msg.strip()

    def timeout_with_failure_msg(self) -> str:
        return "Action failed to Run Script on any entities successfully until timeout."


@output_handler
def main() -> NoReturn:
    siemplify = SiemplifyAction()
    siemplify.script_name = constants.RUN_SCRIPT_SCRIPT_NAME
    action = RunScriptAction(siemplify)
    action.run()


if __name__ == "__main__":
    main()
