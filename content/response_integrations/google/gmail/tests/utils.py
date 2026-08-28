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

import pathlib
import os
import re

from TIPCommon.base.action import Action
from TIPCommon.smp_time import unix_now
from TIPCommon.types import SingleJson

from integration_testing.aiohttp.session import HistoryRecordsList
from integration_testing.request import HttpMethod
from integration_testing.aiohttp.session import HistoryRecord


def init_async_action(
        cls: type[Action],
        script_name: str,
        sync_timeout_ms: int = 60_000,
        async_timeout_ms: int = 600_000,
) -> Action:
    """Init async action for tests."""
    action = cls(script_name)
    action._is_first_run = True
    action.soar_action.script_timeout_deadline = unix_now() + sync_timeout_ms
    action.soar_action.execution_deadline_unix_time_ms = unix_now() + sync_timeout_ms
    action.soar_action.async_total_duration_deadline = unix_now() + async_timeout_ms
    return action


def assert_all_add_evidence(
        history: list[HistoryRecord],
        start: int = 0,
        stop: int = -1
):
    """Assert that all history records are for add evidence call."""
    return all(
        re.search("/api/external/v1/cases/AddEvidence/", hr.request.url.path)
        for hr in history[start:stop]
    )


def assert_all_list_messages(
        history_records: HistoryRecordsList,
        start: int = 0,
        stop: int = -1
) -> None:
    """Assert that all history records are for list messages request."""
    history_records.assert_url_path_with_regex(
        r"/gmail/v1/users/[a-zA-Z]+@[a-zA-Z]+\.[a-zA-Z]+/messages",
        start=start,
        stop=stop,
    )


def assert_all_delete_messages(
        history_records: HistoryRecordsList,
        start: int = 0,
        stop: int = -1
) -> None:
    """Assert that all history records are delete message request."""
    history_records.assert_url_path_with_regex(
        r"/gmail/v1/users/[a-zA-Z]+@[a-zA-Z]+\.[a-zA-Z]+/messages/\w{16}",
        start=start,
        stop=stop,
    )
    assert all(
        hr.request.method == HttpMethod.DELETE
        for hr in history_records[start:stop]
    )


def assert_all_trash_messages(
        history_records: HistoryRecordsList,
        start: int = 0,
        stop: int = -1
) -> None:
    """Assert that all history records are trash message request."""
    history_records.assert_url_path_with_regex(
        r"/gmail/v1/users/[a-zA-Z]+@[a-zA-Z]+\.[a-zA-Z]+/messages/\w{16}/trash",
        start=start,
        stop=stop,
    )
    assert all(
        hr.request.method == HttpMethod.POST
        for hr in history_records[start:stop]
    )


def assert_all_get_message(
        history_records: HistoryRecordsList,
        start: int = 0,
        stop: int = -1
) -> None:
    """Assert that all history records are for get message request."""
    history_records.assert_url_path_with_regex(
        r"/gmail/v1/users/[a-zA-Z]+@[a-zA-Z]+\.[a-zA-Z]+/messages/\w{16}",
        start=start,
        stop=stop,
    )


def assert_all_get_attachment(
        history_records: HistoryRecordsList,
        start: int = 0,
        stop: int = -1
) -> None:
    """Assert that all history records are for get attachment request."""
    history_records.assert_url_path_with_regex(
        (
            r"/gmail/v1/users/[a-zA-Z]+@[a-zA-Z]+\.[a-zA-Z]+/messages"
            r"/\w{16}/attachments/\w+"
        ),
        start=start,
        stop=stop,
    )


def assert_create_label(
    history_records: HistoryRecordsList,
    index: int = 0,
):
    """Assert that a history record on given index is a create labels request."""
    history_records.assert_url_path_with_regex(
        r"/gmail/v1/users/[a-zA-Z]+@[a-zA-Z]+\.[a-zA-Z]+/labels",
        start=index,
        stop=index
    )
    assert history_records[index].request.method == HttpMethod.POST


def assert_list_labels(
    history_records: HistoryRecordsList,
    index: int = 0,
):
    """Assert that a history record on given index is a list labels request."""
    history_records.assert_url_path_with_regex(
        r"/gmail/v1/users/[a-zA-Z]+@[a-zA-Z]+\.[a-zA-Z]+/labels",
        start=index,
        stop=index
    )


def assert_batch_modify(
        history_records: HistoryRecordsList,
        index: int = -1,
) -> None:
    """Assert that all history records are for send message request."""
    history_records.assert_url_path_with_regex(
        r"/gmail/v1/users/[a-zA-Z]+@[a-zA-Z]+\.[a-zA-Z]+/messages/batchModify",
        start=index,
        stop=index,
    )
    assert history_records[index].request.method == HttpMethod.POST


def assert_all_send_message(
        history_records: HistoryRecordsList,
        start: int = 0,
        stop: int = -1
) -> None:
    """Assert that all history records are for send message request."""
    history_records.assert_url_path_with_regex(
        r"/gmail/v1/users/[a-zA-Z]+@[a-zA-Z]+\.[a-zA-Z]+/messages/send",
        start=start,
        stop=stop,
    )
    assert all(
        hr.request.method == HttpMethod.POST
        for hr in history_records[start:stop]
    )


def create_test_attachment(path: str, attachment_name: str) -> str:
    """
    Create a test attachment

    Returns:
        str: path to created attachemnt
    """
    attachment_content = b"This is a test content"

    if not os.path.exists(path):
        os.makedirs(path)

    local_path = os.path.join(path, attachment_name)

    with open(local_path, "wb") as f:
        f.write(attachment_content)

    return local_path


def delete_test_attachments(path: str):
    """
    Delete test attachment

    Args:
        path (str): CSV of path to test attachments
    """
    for file in path.split(","):
        try:
            os.remove(file)
        except FileNotFoundError:
            # File not found
            pass


def assert_get_thread(
    history_records: HistoryRecordsList,
    index: int,
):
    """Assert that a history record on given index is a get thread request."""
    history_records.assert_url_path_with_regex(
        r"/gmail/v1/users/[a-zA-Z]+@[a-zA-Z]+\.[a-zA-Z]+/threads/\w{16}",
        start=index,
        stop=index
    )


def extract_metadata_from_message(
        message: SingleJson,
        fields_to_extract: tuple[str] | None = None
) -> SingleJson:
    """Extract only metadata from message's payload."""
    if fields_to_extract is None:
        fields_to_extract = (
            "id",
            "threadId",
            "labelIds",
            "snippet",
            ("payload", ("mimeType", "headers")),
            "sizeEstimate",
            "historyId",
            "internalDate"
        )

    message_metadata = {}
    for field in fields_to_extract:
        if isinstance(field, tuple):
            message_metadata[field[0]] = extract_metadata_from_message(
                message[field[0]],
                field[1]
            )
            continue

        if field not in message:
            continue

        message_metadata[field] = message[field]

    return message_metadata
