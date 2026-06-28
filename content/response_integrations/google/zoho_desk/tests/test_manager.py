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
import json
import os
import random
import string

import pytest

from zoho_desk.core import ZohoDeskExceptions
from zoho_desk.core.datamodels import Agent, Comment, Ticket


# Constants
_MOCK_FILE = os.path.join(os.path.dirname(__file__), "mock_data.json")
with open(_MOCK_FILE, encoding="UTF-8") as f:
    MOCK_DATA = json.loads(f.read())


@pytest.mark.parametrize("ticket_id, additional_fields", [(115142000000219090, {})])
def test_get_ticket(
    zoho_desk_manager,
    mocker,
    ticket_id,
    additional_fields,
):
    res = mocker.spy(zoho_desk_manager.parser, "build_ticket_object")
    mock_data = MOCK_DATA.get("get_ticket")
    mock_get = mocker.Mock()
    mock_get.json.return_value = mock_data
    mocker.patch.object(
        zoho_desk_manager.session, "get",
        return_value=mock_get,
    )
    ticket = zoho_desk_manager.get_ticket(ticket_id, additional_fields)

    mock_ticket = Ticket(
        raw_data=mock_data,
        id=mock_data.get("id"),
        subject=mock_data.get("subject"),
        description=mock_data.get("description"),
        ticket_number=mock_data.get("ticketNumber"),
        status=mock_data.get("status"),
        created_time=mock_data.get("createdTime"),
        resolution=mock_data.get("resolution"),
        email=mock_data.get("email"),
        first_name=mock_data.get("contact", {}).get("firstName"),
        last_name=mock_data.get("contact", {}).get("lastName"),
    )
    assert mock_ticket.ticket_number == ticket.ticket_number
    assert mock_ticket.id == ticket.id
    assert mock_ticket.subject == ticket.subject
    assert mock_ticket.created_time == ticket.created_time
    assert mock_ticket.status == ticket.status
    assert mock_ticket.description == ticket.description
    assert res.call_count == 1


@pytest.mark.parametrize("ticket_id, limit", [(115142000000176001, 10)])
def test_get_ticket_comments(zoho_desk_manager, mocker, ticket_id, limit):
    res = mocker.spy(zoho_desk_manager.parser, "build_comment_object")
    mock_data = MOCK_DATA.get("get_ticket_comment")
    mock_get = mocker.Mock()
    mock_get.json.return_value = mock_data
    mocker.patch.object(
        zoho_desk_manager.session, "get",
        return_value=mock_get,
    )

    comment = zoho_desk_manager.get_ticket_comments(ticket_id, limit)

    mock_comment = Comment(
        raw_data=mock_data,
        content=mock_data.get("data")[0].get("content"),
        commented_time=mock_data.get("data")[0].get("commentedTime"),
    )
    assert mock_comment.content == comment[0].content
    assert mock_comment.commented_time == comment[0].commented_time
    assert res.call_count == 1


@pytest.mark.parametrize(
    "ticket_id, mark_contact, mark_other_contact_tickets",
    [(115142000000176001, False, False)],
)
def test_mark_ticket_as_spam(
    zoho_desk_manager, mocker, ticket_id, mark_contact, mark_other_contact_tickets
):
    mock_post = mocker.Mock()
    mocker.patch.object(
        zoho_desk_manager.session, "post",
        return_value=mock_post,
    )
    result = zoho_desk_manager.mark_ticket_as_spam(
        ticket_id, mark_contact, mark_other_contact_tickets
    )

    assert result is None


@pytest.mark.parametrize("ticket_id", [115142000000176001])
def test_mark_ticket_as_read(zoho_desk_manager, mocker, ticket_id):
    mock_post = mocker.Mock()
    mocker.patch.object(
        zoho_desk_manager.session, "post",
        return_value=mock_post,
    )
    result = zoho_desk_manager.mark_ticket_as_read(ticket_id)

    assert result is True


@pytest.mark.parametrize("ticket_id", [115142000000176001])
def test_mark_ticket_as_unread(zoho_desk_manager, mocker, ticket_id):
    mock_post = mocker.Mock()
    mocker.patch.object(
        zoho_desk_manager.session, "post",
        return_value=mock_post,
    )
    result = zoho_desk_manager.mark_ticket_as_unread(ticket_id)

    assert result is True


@pytest.mark.parametrize(
    "ticket_id, is_public, content_type, content",
    [(115142000000222369, True, "html", "hello")],
)
def test_add_comment(
    zoho_desk_manager, mocker, ticket_id, is_public, content_type, content
):
    mock_post = mocker.Mock()
    mocker.patch.object(
        zoho_desk_manager.session, "post",
        return_value=mock_post,
    )
    result = zoho_desk_manager.add_comment(ticket_id, is_public, content_type, content)

    assert result is None


@pytest.mark.parametrize("agent_name", ["Milen"])
def test_find_agent(zoho_desk_manager, mocker, agent_name):
    result = mocker.spy(zoho_desk_manager.parser, "build_agent_object")
    mock_data = MOCK_DATA.get("find_agents")
    mock_get = mocker.Mock()
    mock_get.json.return_value = mock_data
    mocker.patch.object(
        zoho_desk_manager.session, "get",
        return_value=mock_get,
    )
    try:
        agent_data = zoho_desk_manager.find_agent(name=agent_name)
    except ZohoDeskExceptions.ZohoDeskException:
        pass

    agent = Agent(
        raw_data=mock_data,
        id=mock_data.get("data")[0].get("id"),
        name=mock_data.get("data")[0].get("name"),
        email=mock_data.get("data")[0].get("emailId"),
    )

    assert agent.id == agent_data[0].id
    assert agent.name == agent_data[0].name
    assert agent.email == agent_data[0].email
    assert result.call_count == 2


@pytest.mark.parametrize(
    "contact_id, department_id, priority, classification",
    [("115142000000244013", "115142000000007061", "High", "Feature")],
)
def test_create_ticket(
    zoho_desk_manager, contact_id, department_id, priority, classification, mocker
):
    # set up a spy mock on function args
    result = mocker.spy(zoho_desk_manager.parser, "build_ticket_object")

    mock_data = MOCK_DATA.get("create_ticket")
    mock_request = mocker.Mock()
    mock_request.json.return_value = mock_data
    mocker.patch.object(
        zoho_desk_manager.session, "post",
        return_value=mock_request,
    )

    title = "".join(random.choice(string.ascii_letters) for _ in range(5))
    test_title = f"test_title_{title}"

    description = "".join(random.choice(string.ascii_letters) for _ in range(5))
    test_description = f"test_description_{description}"

    ticket = zoho_desk_manager.create_ticket(
        title=test_title,
        description=test_description,
        contact_id=contact_id,
        department_id=department_id,
        priority=priority,
        classification=classification,
        assignee_id=None,
        team_id=None,
        channel=None,
        category=None,
        sub_category=None,
        due_date=None,
        custom_fields=None,
    )

    # THEN
    assert mock_data["id"] == ticket.id
    assert mock_data["description"] == ticket.description
    assert result.call_count == 1


def test_update_ticket(zoho_desk_manager, mocker):
    result = mocker.spy(zoho_desk_manager.parser, "build_ticket_object")

    mock_data = MOCK_DATA.get("update_ticket")
    mock_request = mocker.Mock()
    mock_request.json.return_value = mock_data
    mocker.patch.object(
        zoho_desk_manager.session, "patch",
        return_value=mock_request,
    )

    title = "".join(random.choice(string.ascii_letters) for _ in range(5))
    new_test_title = f"new_test_title_{title}"

    description = "".join(random.choice(string.ascii_letters) for _ in range(5))
    new_test_description = f"new_test_description_{description}"

    update_data = zoho_desk_manager.update_ticket(
        ticket_id=mock_data.get("id"),
        title=new_test_title,
        description=new_test_description,
    )

    assert mock_data["id"] == update_data.id
    assert mock_data["subject"] == update_data.subject
    assert mock_data["description"] == update_data.description
    assert result.call_count == 1
