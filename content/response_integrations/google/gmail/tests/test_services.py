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

import asyncio
import pathlib

import pytest

from ..core.GoogleGmailApiManager import (
    ENDPOINTS,
    GoogleGmailApiManager
)
from ..core.GoogleGmailDatamodel import (
    MailboxReadEnum
)
from ..core.GoogleGmailServices import (
    MessagesService
)

from ..tests.core.async_session import GoogleGmailAsyncSession
from ..tests.core.google_gmail import GoogleGmail
from ..tests.utils import (
    assert_all_list_messages,
    assert_all_get_message,
    assert_all_get_attachment,
    assert_get_thread,
)
from integration_testing.common import get_def_file_content
from integration_testing.request import HttpMethod


MOCK_DATA_PATH = pathlib.Path(__file__).parent / "mock_data.json"
MOCK_DATA = get_def_file_content(MOCK_DATA_PATH)


@pytest.mark.anyio
async def test_list_messages(
        google_gmail: GoogleGmail,
        google_gmail_api_manager: GoogleGmailApiManager,
        gmail_script_session: GoogleGmailAsyncSession,
):
    limit = 2
    after_ts = 1719332307
    google_gmail.set_messages(MOCK_DATA["mail_without_attachments"])
    test_user_email = "test@domain.com"

    async with gmail_script_session:
        messages_service = MessagesService(
            user_email=test_user_email,
            api_manager=google_gmail_api_manager
        )
        messages = await asyncio.ensure_future(
            messages_service.list_messages(
                after_ts=after_ts,
                limit=limit,
                mailbox_read_status=MailboxReadEnum.READ
            ),
            loop=asyncio.get_running_loop()
        )

    assert messages and len(messages) <= limit
    assert messages == sorted(messages, key=lambda m: m.internal_date)
    assert all(m.internal_date >= after_ts * 1000 for m in messages)
    assert all(message.to_json() for message in messages)

    assert_all_list_messages(gmail_script_session.request_history, stop=-2)
    assert_all_get_message(gmail_script_session.request_history, start=-2)


@pytest.mark.anyio
async def test_search_by_message_id(
        google_gmail: GoogleGmail,
        google_gmail_api_manager: GoogleGmailApiManager,
        gmail_script_session: GoogleGmailAsyncSession,
):
    google_gmail.set_messages(MOCK_DATA["mail_without_attachments"])
    test_user_email = "test@domain.com"

    async with gmail_script_session:
        messages_service = MessagesService(
            user_email=test_user_email,
            api_manager=google_gmail_api_manager
        )
        messages = await asyncio.ensure_future(
            messages_service.search_by_message_id(
                message_id=(
                    "<CAAfJ0RhhZBGtbvyx1YfAUQcWByMP2UuG2oKk2mEdZ_XCiEuLRw"
                    "@mail.gmail.com>"
                )
            ),
            loop=asyncio.get_running_loop()
        )

    assert len(messages) == 1 and messages[0] == "19050407063955c1"
    assert_all_list_messages(gmail_script_session.request_history)


@pytest.mark.anyio
async def test_trash_message(
        google_gmail_api_manager: GoogleGmailApiManager,
        gmail_script_session: GoogleGmailAsyncSession,
):
    test_user_email = "test@domain.com"
    message_id = "19050407063955c1"

    async with gmail_script_session:
        messages_service = MessagesService(
            user_email=test_user_email,
            api_manager=google_gmail_api_manager
        )
        await asyncio.ensure_future(
            messages_service.trash_message(
                message_id=message_id
            ),
            loop=asyncio.get_running_loop()
        )

    gmail_script_session.request_history.assert_url_path_with_regex(
        ENDPOINTS["users.messages.trash"].format(
            user_email=test_user_email,
            message_id=message_id
        )
    )
    assert gmail_script_session.request_history[-1].request.method == HttpMethod.POST


@pytest.mark.anyio
async def test_delete_message(
        google_gmail_api_manager: GoogleGmailApiManager,
        gmail_script_session: GoogleGmailAsyncSession,
):
    test_user_email = "test@domain.com"
    message_id = "19050407063955c1"

    async with gmail_script_session:
        messages_service = MessagesService(
            user_email=test_user_email,
            api_manager=google_gmail_api_manager
        )
        await asyncio.ensure_future(
            messages_service.delete_message(
                message_id=message_id
            ),
            loop=asyncio.get_running_loop()
        )

    gmail_script_session.request_history.assert_url_path_with_regex(
        ENDPOINTS["users.messages.details"].format(
            user_email=test_user_email,
            message_id=message_id
        )
    )
    assert gmail_script_session.request_history[-1].request.method == HttpMethod.DELETE


@pytest.mark.anyio
async def test_enrich_attachments(
        google_gmail: GoogleGmail,
        google_gmail_api_manager: GoogleGmailApiManager,
        gmail_script_session: GoogleGmailAsyncSession,
):
    limit = 2
    after_ts = 1721894511
    google_gmail.set_messages(MOCK_DATA["mail_with_eml"] + MOCK_DATA["mail_with_files"])
    google_gmail.set_attachments(MOCK_DATA["attachments"])
    test_user_email = "test@domain.com"

    async with gmail_script_session:
        messages_service = MessagesService(
            user_email=test_user_email,
            api_manager=google_gmail_api_manager
        )
        messages = await asyncio.ensure_future(
            messages_service.list_messages(
                after_ts=after_ts,
                limit=limit,
                mailbox_read_status=MailboxReadEnum.READ
            )
        )
        for message in messages:
            await asyncio.ensure_future(
                messages_service.enrich_attachments(
                    message_id=message.id,
                    message_part=message.payload
                )
            )

    assert len(messages) == 2
    assert all(message.to_json() for message in messages)

    assert_all_list_messages(gmail_script_session.request_history, stop=1)
    assert_all_get_message(gmail_script_session.request_history, start=1, stop=3)
    assert_all_get_attachment(gmail_script_session.request_history, start=3)


@pytest.mark.anyio
async def test_get_thread(
        google_gmail: GoogleGmail,
        google_gmail_api_manager: GoogleGmailApiManager,
        gmail_script_session: GoogleGmailAsyncSession,
):
    google_gmail.set_messages(MOCK_DATA["mail_without_attachments"])
    thread_id = google_gmail.add_thread(MOCK_DATA["mail_without_attachments"])
    test_user_email = "test@domain.com"

    async with gmail_script_session:
        messages_service = MessagesService(
            user_email=test_user_email,
            api_manager=google_gmail_api_manager
        )
        thread = await asyncio.ensure_future(
            messages_service.get_thread_by_id(thread_id),
            loop=asyncio.get_running_loop()
        )

    assert_get_thread(gmail_script_session.request_history, 1)
    assert thread.to_json()


@pytest.mark.anyio
async def test_batch_modify(
        google_gmail_api_manager: GoogleGmailApiManager,
        gmail_script_session: GoogleGmailAsyncSession,
):
    test_user_email = "test@domain.com"
    message_id = "19050407063955c1"

    async with gmail_script_session:
        messages_service = MessagesService(
            user_email=test_user_email,
            api_manager=google_gmail_api_manager
        )
        await asyncio.ensure_future(
            messages_service.add_labels(
                message_ids=[message_id],
                label_ids=["testLabel"]
            ),
            loop=asyncio.get_running_loop()
        )
        await asyncio.ensure_future(
            messages_service.remove_labels(
                message_ids=[message_id],
                label_ids=["testLabel"]
            ),
            loop=asyncio.get_running_loop()
        )

    gmail_script_session.request_history.assert_url_path_with_regex(
        ENDPOINTS["users.messages.batchModify"].format(
            user_email=test_user_email,
        )
    )
    assert gmail_script_session.request_history[-2].request.method == HttpMethod.POST
    assert gmail_script_session.request_history[-1].request.method == HttpMethod.POST
