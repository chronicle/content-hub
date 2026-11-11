from __future__ import annotations

import json
import time
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from TIPCommon.base.action import Action
from TIPCommon.base.action.data_models import EntityTypesEnum
from TIPCommon.extraction import extract_action_param
from TIPCommon.transformation import string_to_multi_value
from TIPCommon.utils import get_entity_original_identifier
from TIPCommon.validation import ParameterValidator
from g_suite.core import consts
from g_suite.core.GSuiteManager import GSuiteManager
from g_suite.core.action_init import create_api_client
from g_suite.core.datamodels import UserActivityEvent
from g_suite.core.exceptions import (
    GSuiteManagerError,
    GSuiteValidationException,
    GSuiteParameterValidationError,
)

if TYPE_CHECKING:
    from typing import Any, Generator
    from TIPCommon.types import SingleJson


class SearchUserActivityEventsAction(Action):

    def __init__(self) -> None:
        super().__init__(consts.SEARCH_USER_ACTIVITY_EVENTS_SCRIPT_NAME)
        self.manager: GSuiteManager | None = None
        self.output_message: str = ""
        self.result_value: bool = False
        self.json_results: list = []

    def _init_api_clients(self) -> None:
        self.manager: GSuiteManager = create_api_client(self.soar_action)

    def _extract_action_parameters(self) -> None:
        raw_emails = extract_action_param(
            self.soar_action,
            param_name="User Email Addresses",
        )
        self.params.user_email_addresses: list[str] = (
            string_to_multi_value(raw_emails) if raw_emails else []
        )

        self.params.raw_apps: str = extract_action_param(
            self.soar_action,
            param_name="Application Names",
            is_mandatory=True,
        )

        raw_events: str | None = extract_action_param(
            self.soar_action,
            param_name="Event Type Filter",
        )
        self.params.event_type_filter: list[str] = (
            string_to_multi_value(raw_events) if raw_events else []
        )

        self.params.time_frame: str = extract_action_param(
            self.soar_action,
            param_name="Time Frame",
            default_value=consts.LAST_HOUR,
        )
        self.params.start_time: str | None = extract_action_param(
            self.soar_action,
            param_name="Start Time",
        )
        self.params.end_time: str | None = extract_action_param(
            self.soar_action,
            param_name="End Time",
        )
        self.params.max_events_to_return: int = extract_action_param(
            self.soar_action,
            param_name="Max Events To Return",
            default_value=consts.DEFAULT_MAX_EVENTS_SEARCH,
            input_type=int,
        )

    def _validate_params(self) -> None:
        validator = ParameterValidator(self.soar_action)
        self._parse_and_validate_application_names()

        if (
            self.params.start_time or self.params.end_time
        ) and self.params.time_frame != "Custom":
            raise GSuiteParameterValidationError(
                "Start Time or End Time can only be provided when 'Custom' is "
                "selected for the Time Frame parameter."
            )

        validator.validate_range(
            param_name="Max Events To Return",
            value=self.params.max_events_to_return,
            min_limit=consts.MINIMUM_POSITIVE_INTEGER,
            max_limit=consts.MAX_EVENTS_LIMIT_SEARCH,
        )

        if self.params.time_frame == consts.CUSTOM:
            self._validate_custom_time_frame()
        else:
            self.params.start_time, self.params.end_time = self._get_time_frame_iso(
                self.params.time_frame
            )

    def _perform_action(self, _: Any = None) -> None:
        target_users: set[str] = self._get_target_users()
        if not target_users:
            raise GSuiteValidationException(
                "No users were provided to run the action on. Please provide at least "
                "one valid user entity (email address)."
            )

        self.logger.info(
            f"Action will run on the following users: {', '.join(target_users)}"
        )

        successful_users: list[str]
        failed_users: list[str]
        json_results: list[SingleJson]
        successful_users, failed_users, json_results = self._process_users(target_users)
        self._process_results(successful_users, failed_users, json_results)

    def _parse_and_validate_application_names(self) -> None:
        display_names: list[str] = self._parse_application_names_json()
        self.params.application_names = self._map_display_names_to_api_names(
            display_names
        )

        if not self.params.application_names:
            raise GSuiteValidationException(
                "No valid application names were provided. Please select at least one "
                "valid application from the list."
            )

    def _parse_application_names_json(self) -> list[str]:
        try:
            apps_list: list[Any] = json.loads(self.params.raw_apps)
            if not isinstance(apps_list, list):
                raise GSuiteValidationException(
                    "Invalid format for 'Application Names'. "
                    "Expected a JSON array of strings."
                )
            return [str(item) for item in apps_list]
        except json.JSONDecodeError as e:
            raise GSuiteValidationException(
                f"Invalid JSON format for 'Application Names'. "
                f"Please provide a valid JSON array of strings. Error: {e}"
            ) from e

    def _map_display_names_to_api_names(
        self,
        display_names: list[str],
    ) -> list[str]:
        if consts.ALL_APPLICATIONS_KEY in display_names:
            return list(consts.APPLICATION_NAMES)

        api_names = [
            consts.APPLICATION_NAME_MAPPING.get(name) for name in display_names
        ]

        return [name for name in api_names if name]

    def _validate_custom_time_frame(self) -> None:
        if not self.params.start_time:
            raise GSuiteValidationException(
                "Start Time is required when Time Frame is set to 'Custom'."
            )
        self._validate_iso_time_string(self.params.start_time, "Start Time")

        if self.params.end_time:
            self._validate_iso_time_string(self.params.end_time, "End Time")
            return

        self.params.end_time = datetime.utcnow().isoformat() + "Z"
        return

    def _validate_iso_time_string(
        self,
        time_str: str,
        param_name: str,
    ) -> None:
        try:
            datetime.fromisoformat(time_str.replace("Z", "+00:00"))

        except ValueError as exc:
            raise GSuiteValidationException(
                f"Invalid {param_name} format. Please use ISO 8601 format "
                f"(e.g., YYYY-MM-DDTHH:MM:SSZ)."
            ) from exc

    def _get_target_users(self) -> set[str]:
        target_users: set[str] = set(self.params.user_email_addresses)

        user_entities: set[str] = {
            get_entity_original_identifier(entity)
            for entity in self.soar_action.target_entities
            if entity.entity_type == EntityTypesEnum.USER.value
        }
        target_users.update(user_entities)

        return target_users

    def _process_users(
        self,
        target_users: set[str],
    ) -> tuple[list[str], list[str], list[SingleJson]]:
        successful_users: list[str] = []
        failed_users: list[str] = []
        json_results: list[SingleJson] = []

        for user in target_users:
            if self._is_approaching_timeout():
                self.logger.info("Action is approaching timeout. Aborting.")
                break

            self._process_single_user(
                user, successful_users, failed_users, json_results
            )

        return successful_users, failed_users, json_results

    def _process_single_user(
        self,
        user: str,
        successful_users: list[str],
        failed_users: list[str],
        json_results: list[SingleJson],
    ) -> None:
        self.logger.info(f"Processing events for user: {user}")
        try:
            user_events: list[UserActivityEvent] = (
                self._get_and_process_events_for_user(user)
            )
            self._handle_user_event_results(
                user, user_events,
                successful_users,
                failed_users,
                json_results,
            )

        except GSuiteManagerError as e:
            self.logger.info(f"Error processing user {user}: {e}")
            failed_users.append(user)

    def _get_and_process_events_for_user(
        self,
        user_key: str,
    ) -> list[UserActivityEvent]:
        collected_events: list[UserActivityEvent] = (
            self._collect_events_from_apps_for_user(user_key)
        )
        collected_events.sort(key=lambda e: e.id.get("time", ""), reverse=True)

        return collected_events[: self.params.max_events_to_return]

    def _collect_events_from_apps_for_user(
        self,
        user_key: str,
    ) -> list[UserActivityEvent]:
        collected_events: list[UserActivityEvent] = []
        for app_name in self.params.application_names:
            app_events: list[UserActivityEvent] = self._fetch_events_for_app(
                user_key,
                app_name,
            )
            if not app_events:
                continue

            filtered_app_events: list[UserActivityEvent] = self._filter_events_by_type(
                app_events
            )
            collected_events.extend(filtered_app_events)

            if len(collected_events) >= self.params.max_events_to_return:
                self.logger.info(
                    f"Reached event limit for user '{user_key}' after querying app "
                    f"'{app_name}'. Skipping remaining applications for this user."
                )
                break

        return collected_events

    def _fetch_events_for_app(
        self,
        user_key: str,
        app_name: str,
    ) -> list[UserActivityEvent]:
        self.logger.info(
            f"Querying application '{app_name}' for user '{user_key}'"
        )

        return self.manager.list_user_activity_events(
            user_key=user_key,
            application_name=app_name,
            start_time=self.params.start_time,
            end_time=self.params.end_time,
            limit=consts.MAX_EVENTS_LIMIT_SEARCH,
        )

    def _filter_events_by_type(
        self,
        events: list[UserActivityEvent],
    ) -> list[UserActivityEvent]:
        if not self.params.event_type_filter:
            return events

        return [
            event
            for event in events
            if any(
                sub_event.get("name") in self.params.event_type_filter
                for sub_event in event.events
            )
        ]

    def _handle_user_event_results(
        self,
        user: str,
        user_events: list[UserActivityEvent],
        successful_users: list[str],
        failed_users: list[str],
        json_results: list[SingleJson],
    ) -> None:
        if not user_events:
            reason: str = f"No events for user {user} matched the specified filters."
            self._process_failed_event_find(user, failed_users, reason)
            return

        self.logger.info(
            f"Found {len(user_events)} raw events for user {user}. "
            "Filtering for unique events."
        )
        formatted_events: list[SingleJson] = self._format_events_for_json_result(
            user_events
        )

        if formatted_events:
            self._process_successful_event_find(
                user, formatted_events, successful_users, json_results
            )
        else:
            reason: str = (
                f"No unique events found for user {user} after de-duplication."
            )
            self._process_failed_event_find(user, failed_users, reason)

    def _process_successful_event_find(
        self,
        user: str,
        formatted_events: list[SingleJson],
        successful_users: list[str],
        json_results: list[SingleJson],
    ) -> None:
        self.logger.info(
            f"Found {len(formatted_events)} unique events for user {user}."
        )
        successful_users.append(user)
        json_results.append({"Entity": user, "EntityResult": formatted_events})

    def _process_failed_event_find(
        self,
        user: str,
        failed_users: list[str],
        reason: str,
    ) -> None:
        self.logger.info(reason)
        failed_users.append(user)

    def _format_events_for_json_result(
        self,
        events: list[UserActivityEvent],
    ) -> list[SingleJson]:
        unique_events: list[SingleJson] = []
        seen_events: set[tuple[str | None, str | None, str | None]] = set()

        all_sub_events: Generator[tuple[UserActivityEvent, SingleJson], None, None] = (
            (event_record, sub_event)
            for event_record in events
            for sub_event in event_record.events
        )

        for event_record, sub_event in all_sub_events:
            signature: tuple[str | None, str | None, str | None] = (
                self._create_event_signature(event_record, sub_event)
            )
            if signature not in seen_events:
                seen_events.add(signature)
                unique_events.append(self._create_json_event(event_record, sub_event))

        return unique_events

    def _create_event_signature(
        self,
        event_record: UserActivityEvent,
        sub_event: SingleJson,
    ) -> tuple[str | None, str | None, str | None]:
        return (
            event_record.id.get("applicationName"),
            sub_event.get("type"),
            sub_event.get("name"),
        )

    def _create_json_event(
        self,
        event_record: UserActivityEvent,
        sub_event: SingleJson,
    ) -> SingleJson:
        return {
            "applicationName": event_record.id.get("applicationName"),
            "type": sub_event.get("type"),
            "name": sub_event.get("name"),
            "parameters": sub_event.get("parameters", []),
        }

    def _process_results(
        self,
        successful_users: list[str],
        failed_users: list[str],
        json_results: list[SingleJson],
    ) -> None:
        output_messages: list[str] = []
        self.result_value = bool(successful_users)

        if successful_users:
            output_messages.append(
                "Successfully found events for the following users in Google "
                f"Workspace: {', '.join(successful_users)}."
            )
            result_to_add: list[SingleJson] | SingleJson = (
                json_results[0] if len(json_results) == 1 else json_results
            )
            self.json_results = result_to_add

        if failed_users:
            output_messages.append(
                "No events were found for the following users in Google "
                f"Workspace: {', '.join(failed_users)}."
            )

        if not output_messages:
            self.output_message = (
                "No events were found for the provided users in Google Workspace."
            )
        else:
            self.output_message = "\n".join(output_messages)

    def _is_approaching_timeout(self) -> bool:
        return (
            self.soar_action.execution_deadline_unix_time_ms - (time.time() * 1000)
            < consts.SEARCH_USER_ACTIVITY_EVENTS_TIMEOUT_THRESHOLD_MS
        )

    def _get_time_frame_iso(
        self,
        time_frame_str: str,
    ) -> tuple[str, str]:
        now: datetime = datetime.utcnow()
        delta: timedelta | None = consts.TIMEDELTA_MAP.get(time_frame_str)

        if delta is None:
            raise GSuiteValidationException(
                f"Invalid time frame provided: {time_frame_str}"
            )

        start_time: datetime = now - delta

        return start_time.isoformat() + "Z", now.isoformat() + "Z"

    def _create_csv_from_events(
        self,
        events: list[UserActivityEvent],
    ) -> list[SingleJson]:
        return [
            self._create_csv_row(event_record, sub_event)
            for event_record in events
            for sub_event in event_record.events
        ]

    def _create_csv_row(
        self,
        event_record: UserActivityEvent,
        sub_event: SingleJson,
    ) -> SingleJson:
        params_str: str = self._format_csv_parameters(sub_event.get("parameters", []))

        return {
            "Time": event_record.id.get("time"),
            "Actor": event_record.actor.get("email"),
            "IP Address": event_record.ip_address or "N/A",
            "Event Type": sub_event.get("type"),
            "Event Name": sub_event.get("name"),
            "Parameters": params_str,
        }

    def _format_csv_parameters(
        self,
        params_list: list[SingleJson],
    ) -> str:
        return ", ".join(
            f"{p['name']}:{p.get('value', p.get('multiValue', ''))}"
            for p in params_list
        )


def main() -> None:
    action = SearchUserActivityEventsAction()
    action.run()


if __name__ == "__main__":
    main()
