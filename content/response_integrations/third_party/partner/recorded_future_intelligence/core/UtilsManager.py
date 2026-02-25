############################## TERMS OF USE ################################### # noqa: E266
# The following code is provided for demonstration purposes only, and should  #
# not be used without independent verification. Recorded Future makes no      #
# representations or warranties, express, implied, statutory, or otherwise,   #
# regarding this code, and provides it strictly "as-is".                      #
# Recorded Future shall not be liable for, and you assume all risk of         #
# using the foregoing.                                                        #
###############################################################################

from __future__ import annotations

from datetime import datetime

import requests

from .constants import (
    CONNECTOR_DATETIME_FORMAT,
    DATETIME_READABLE_FORMAT,
    ENTITY_CHANGE_CASES,
    PBA_SEVERITY_MAP_INTEGER,
    SANDBOX_TIMEOUT_THRESHOLD_IN_MIN,
)
from .exceptions import (
    RecordedFutureManagerError,
    RecordedFutureNotFoundError,
    RecordedFutureUnauthorizedError,
)


def validate_response(response):
    try:
        response.raise_for_status()

    except requests.HTTPError as error:
        if response.status_code == 404:
            raise RecordedFutureNotFoundError(error)

        if response.status_code == 401:
            raise RecordedFutureUnauthorizedError(error)

        try:
            response.json()
            error = response.json().get("error", []).get("message")
        except AttributeError:
            pass

        raise RecordedFutureManagerError(error)


def format_timestamp(timestamp):
    if not timestamp:
        return ""

    if isinstance(timestamp, str):
        try:
            timestamp = datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%S.%fZ")
        except ValueError:
            timestamp = datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%SZ")

    return timestamp.strftime(DATETIME_READABLE_FORMAT)


def check_errors_in_response(response):
    response.json()
    error = response.json().get("error")

    if len(error) != 0:
        error = error[0].get("reason")
        raise RecordedFutureManagerError(error)


def get_entity_original_identifier(entity):
    """Helper function for getting entity original identifier
    :param entity: entity from which function will get original identifier
    :return: {str} original identifier.
    """
    return entity.additional_properties.get("OriginalIdentifier", entity.identifier)


def get_recorded_future_id(entity):
    """Helper function for getting entity RF id
    :param entity: entity from which function will get RF id
    :return: {str} RF id if exists else empty.
    """
    return entity.additional_properties.get("RF_id", "")


def get_recorded_future_document_id(entity):
    """Helper function for getting entity RF document id
    :param entity: entity from which function will get RF document id
    :return: {str} RF document id if exists else empty.
    """
    return entity.additional_properties.get("RF_doc_id", "")


def is_reopened(playbook_alert_logs: list) -> bool:
    """Helper function to check if Playbook Alert was reopened
    :param playbook_alert_logs: Playbook Alert panel_log_v2
    :return: {bool} If Playbook Alert was reopened.
    """
    if not playbook_alert_logs:
        return False
    status_change_logs = [
        log
        for log in playbook_alert_logs
        for change in log["changes"]
        if change["type"] == "status_change"
    ]
    if not status_change_logs:
        return False
    if len(status_change_logs) > 1:
        status_change_logs = sorted(
            status_change_logs,
            key=lambda log: datetime.strptime(
                log["created"],
                CONNECTOR_DATETIME_FORMAT + "Z",
            ),
            reverse=True,
        )
    playbook_alert_log = status_change_logs[0]  # always most recent if multiple
    changes = playbook_alert_log["changes"]
    if len(changes) > 1:
        changes = [change for change in changes if change["type"] == "status_change"]
    old: bool = changes[0]["old"] in ["Resolved", "Dismissed"]
    new: bool = changes[0]["new"] in ["New", "InProgress"]
    return old and new


def is_priority_increase(playbook_alert_logs: list) -> bool:
    """Helper function to check if Playbook Alert priority increased
    :param playbook_alert_logs: Playbook Alert panel_log_v2
    :return: {bool} If Playbook Alert priority increased.
    """
    if not playbook_alert_logs:
        return False
    priority_change_logs = [
        log
        for log in playbook_alert_logs
        for change in log["changes"]
        if change["type"] == "priority_change"
    ]
    if not priority_change_logs:
        return False
    if len(priority_change_logs) > 1:
        priority_change_logs = sorted(
            priority_change_logs,
            key=lambda log: datetime.strptime(
                log["created"],
                CONNECTOR_DATETIME_FORMAT + "Z",
            ),
            reverse=True,
        )
    playbook_alert_log = priority_change_logs[0]
    changes = playbook_alert_log["changes"]
    if len(changes) > 1:
        changes = [change for change in changes if change["type"] == "priority_change"]
    old = PBA_SEVERITY_MAP_INTEGER[changes[0]["old"]]
    new = PBA_SEVERITY_MAP_INTEGER[changes[0]["new"]]
    return old < new


def is_new_assessment(playbook_alert_logs: list) -> bool:
    """Helper function to check if Playbook Alert has New Assessment
    :param playbook_alert_logs: Playbook Alert panel_log_v2
    :return: {bool} If Playbook Alert has New Assessment.
    """
    if not playbook_alert_logs:
        return False
    assessment = "assessment_ids_change"
    assessment_logs = [
        log
        for log in playbook_alert_logs
        for change in log["changes"]
        if change["type"] == assessment and "added" in change
    ]
    if not assessment_logs:
        return False
    if len(assessment_logs) > 1:
        assessment_logs = sorted(
            assessment_logs,
            key=lambda log: datetime.strptime(
                log["created"],
                CONNECTOR_DATETIME_FORMAT + "Z",
            ),
            reverse=True,
        )
    playbook_alert_log = assessment_logs[0]
    changes = playbook_alert_log["changes"]
    if len(changes) > 1:
        changes = [change for change in changes if change["type"] == assessment]
    return bool(changes)


def is_entity_added(playbook_alert_logs: list) -> bool:
    """Helper function to check if Playbook Alert Entities were added.
    :param playbook_alert_logs: Playbook Alert panel_log_v2
    :return: {bool} If Playbook Alert Entities were added.
    """
    if not playbook_alert_logs:
        return False
    entity_added_logs = [
        log
        for log in playbook_alert_logs
        for change in log["changes"]
        if change["type"] in ENTITY_CHANGE_CASES and change.get("added")
    ]
    if not entity_added_logs:
        return False
    if len(entity_added_logs) > 1:
        entity_added_logs = sorted(
            entity_added_logs,
            key=lambda log: datetime.strptime(
                log["created"],
                CONNECTOR_DATETIME_FORMAT + "Z",
            ),
            reverse=True,
        )
    playbook_alert_log = entity_added_logs[0]
    changes = playbook_alert_log["changes"]
    if len(changes) > 1:
        changes = [
            change
            for change in changes
            if change["type"] in ENTITY_CHANGE_CASES and change.get("added")
        ]
    return bool(changes)


def is_create_new_case(playbook_alert_logs, active_filters) -> bool:
    """Helper function to determine if a new Case should be created
    :param playbook_alert_logs: Playbook Alert panel_log_v2
    :param active_filters: Connector parameters for when to create a new Case
    :return: {bool} If Connector creates a new Case.
    """
    if not playbook_alert_logs:
        return False
    func_map = {
        "reopened": is_reopened,
        "priority_increase": is_priority_increase,
        "new_assessment": is_new_assessment,
        "entity_added": is_entity_added,
    }
    enabled_filters = [k for k, v in active_filters.items() if v and k in func_map]
    for update_use_case in enabled_filters:
        if func_map[update_use_case](playbook_alert_logs):
            return True
    return False


def is_async_action_global_timeout_approaching(siemplify, start_time):
    return (
        siemplify.execution_deadline_unix_time_ms - start_time
        < SANDBOX_TIMEOUT_THRESHOLD_IN_MIN * 60
    )
