from __future__ import annotations

import json
from typing import TYPE_CHECKING

from soar_sdk.SiemplifyDataModel import DomainEntityInfo
from TIPCommon.base.action import Action
from TIPCommon.base.action.data_models import EntityTypesEnum, ExecutionState
from TIPCommon.utils import get_entity_original_identifier
from g_suite.core import consts
from g_suite.core.GSuiteManager import GSuiteManager
from g_suite.core.action_init import create_api_client
from g_suite.core.datamodels import Browser
from g_suite.core.exceptions import GSuiteManagerError

if TYPE_CHECKING:
    from TIPCommon.types import SingleJson
    from typing import Any


class GetHostBrowserDetailsAction(Action[GSuiteManager]):

    def __init__(self) -> None:
        super().__init__(consts.GET_HOST_BROWSER_DETAILS_SCRIPT_NAME)
        self.manager: GSuiteManager | None = None
        self.output_message: str = ""
        self.result_value: bool = False
        self.execution_state: ExecutionState = ExecutionState.IN_PROGRESS
        self.successful_entities: list[str] = []
        self.failed_entities: list[str] = []

    def _init_api_clients(self) -> GSuiteManager:
        self.manager: GSuiteManager = create_api_client(self.soar_action)

    def _get_entity_types(self) -> list[EntityTypesEnum]:
        return [EntityTypesEnum.HOST_NAME]

    def _perform_action(self, entity: DomainEntityInfo) -> None:
        host: str = get_entity_original_identifier(entity)
        try:
            self.logger.info(f"Querying browsers for host: {host}")
            browsers: list[Browser] = self.manager.get_host_browser_details(
                hostname=host
            )

            if browsers:
                self.logger.info(
                    f"Found {len(browsers)} browsers for host {host}."
                )
                self._process_successful_host(host, browsers)
            else:
                self.logger.info(f"No browsers found for host {host}.")
                self.failed_entities.append(host)

        except GSuiteManagerError as e:
            self.logger.error(
                f"Failed to get browser details for {host}: {e}"
            )
            self.failed_entities.append(host)

    def _finalize_action_on_success(self) -> None:
        if self.successful_entities:
            self._set_state_on_success()
        elif self.failed_entities:
            self._set_state_on_failure()
        else:
            self._set_state_on_no_entities_processed()

    def _process_successful_host(self, host: str, browsers: list[Browser]) -> None:
        first_browser: Browser = browsers[0]
        browser_json: SingleJson = first_browser.as_json()
        self._process_browser_policies(browser_json)

        self.json_results[host] = browser_json
        self.successful_entities.append(host)

    def _process_browser_policies(self, browser_json: dict) -> None:
        self._process_policies(browser_json.get("machinePolicies", []))

        b_instances: list[dict] = browser_json.get("browsers", [])
        for b_instance in b_instances:
            profiles: list[dict] = b_instance.get("profiles", [])
            for profile in profiles:
                self._process_policies(profile.get("userPolicies", []))

    def _process_policies(self, policies: list[dict]) -> None:
        for policy in policies:
            self._process_single_policy(policy)

    def _process_single_policy(self, policy: dict[str, Any]) -> None:
        value: Any = policy.get("value")
        if not isinstance(value, str):
            return

        try:
            parsed_value: Any = json.loads(value)
            if isinstance(parsed_value, list):
                policy["value"] = self._process_policy_list_value(parsed_value)
            else:
                policy["value"] = parsed_value
        except (json.JSONDecodeError, TypeError):
            pass

    def _process_policy_list_value(self, parsed_list: list[Any]) -> list[Any]:
        return [self._try_parse_json_item(item) for item in parsed_list]

    def _try_parse_json_item(self, item: Any) -> Any:
        if not isinstance(item, str):
            return item

        try:
            return json.loads(item)
        except (json.JSONDecodeError, TypeError):
            return item

    def _set_state_on_success(self) -> None:
        self.result_value = True
        self.execution_state = ExecutionState.COMPLETED
        output_messages: list[str] = []

        success_msg: str = (
            "Successfully returned browsers related to the following hostnames in "
            f"Google Workspace: {', '.join(self.successful_entities)}."
        )
        output_messages.append(success_msg)

        if self.failed_entities:
            failed_msg: str = (
                "No browsers were associated with the following hostnames in "
                f"Google Workspace: {', '.join(self.failed_entities)}."
            )
            output_messages.append(failed_msg)

        self.output_message = "\n".join(output_messages)

    def _set_state_on_failure(self) -> None:
        self.result_value = False
        self.execution_state = ExecutionState.COMPLETED
        self.output_message = "No browsers were associated with provided hostnames."

    def _set_state_on_no_entities_processed(self) -> None:
        self.result_value = False
        self.execution_state = ExecutionState.COMPLETED
        self.output_message = "No browsers were associated with provided hostnames."


def main() -> None:
    action = GetHostBrowserDetailsAction()
    action.run()


if __name__ == "__main__":
    main()
