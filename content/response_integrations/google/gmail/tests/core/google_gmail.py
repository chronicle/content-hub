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
import abc

import copy
import dataclasses
import datetime
import pathlib

from TIPCommon.consts import NUM_OF_MILLI_IN_SEC
from TIPCommon.types import SingleJson
from integration_testing.common import get_def_file_content

from gmail.tests.utils import extract_metadata_from_message


MOCK_DATA_PATH = pathlib.Path(__file__).parent / "mock_data.json"
MOCK_DATA = get_def_file_content(MOCK_DATA_PATH)


@dataclasses.dataclass
class GoogleGmail(abc.ABC):
    messages: dict[str, SingleJson] = dataclasses.field(default_factory=dict)
    attachments: dict[str, SingleJson] = dataclasses.field(default_factory=dict)
    threads: dict[str, SingleJson] = dataclasses.field(default_factory=dict)

    def list_labels(self) -> list[SingleJson]:
        return MOCK_DATA["labels"]

    def add_thread(self, messages: list[SingleJson]) -> str:
        self.threads[messages[0]["id"]] = {
            "id": messages[0]["id"],
            "historyId": messages[0]["historyId"],
            "messages": [
                extract_metadata_from_message(message) for message in messages
            ]
        }
        return messages[0]["id"]

    def get_thread(self, thread_id: str) -> SingleJson:
        return self.threads[thread_id]

    def set_messages(
            self,
            messages: list[SingleJson],
            set_ts_to_now: bool = False
    ) -> None:
        """Add messages to internal storage."""
        for index, message in enumerate(messages):
            message_ = copy.deepcopy(message)
            if set_ts_to_now is True:
                message_["internalDate"] = str(
                    int(
                        (datetime.datetime.now().timestamp() - index)
                        * NUM_OF_MILLI_IN_SEC
                    )
                )
            self.messages[message_["id"]] = message_

    def set_attachments(self, attachments: dict[str, SingleJson]) -> None:
        self.attachments = attachments

    def get_message(self, message_id: str) -> SingleJson:
        return self.messages[message_id]

    def list_messages(
            self,
            after_ts: str,
            before_ts: str,
            message_id: str,
    ) -> list[SingleJson]:
        """List messages from internal storage according to provided filter."""
        def _filter_by_ts(message: SingleJson) -> bool:
            internal_date = int(message["internalDate"]) // NUM_OF_MILLI_IN_SEC
            if after_ts and internal_date < int(after_ts):
                return False

            if before_ts and internal_date > int(before_ts):
                return False

            return True

        def _filter_by_message_id(message: SingleJson) -> bool:
            headers = {
                header["name"]: header["value"]
                for header in message["payload"]["headers"]
            }
            return not message_id or headers.get("Message-ID") == message_id

        return list(
            filter(
                lambda message: _filter_by_ts(message) & _filter_by_message_id(message),
                self.messages.values()
            )
        )

    def get_attachment(self, attachment_id: str) -> SingleJson:
        return self.attachments[attachment_id]
