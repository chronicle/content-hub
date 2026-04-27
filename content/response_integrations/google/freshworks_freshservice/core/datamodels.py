from __future__ import annotations
import copy
import re
import uuid
from datetime import datetime
from typing import Optional, List, Dict

from TIPCommon import dict_to_flat

from soar_sdk.SiemplifyUtils import convert_datetime_to_unix_time
from .consts import (
    DEVICE_VENDOR,
    DEVICE_PRODUCT,
    TICKET_PRIORITY_TO_SIEM_SEVERITY,
    DATE_FORMAT,
    MAPPED_CONVERSATION_SOURCE_TYPES,
    MAPPED_TICKET_PRIORITIES,
    MAPPED_TICKET_STATUSES,
    MAPPED_TICKET_SOURCES,
    CSV_TABLE_DELIMITER,
)


class BaseModel:
    def __init__(self, raw_data):
        self.raw_data = raw_data

    def to_json(self):
        return self.raw_data

    def to_flat(self):
        return dict_to_flat(self.to_json())

    def to_table(self):
        return [self.to_csv()]

    def to_csv(self):
        return dict_to_flat(self.to_json())

    def is_empty(self):
        return not bool(self.raw_data)


class Ticket(BaseModel):
    """
    Freshservice Ticket
    """

    def __init__(
        self,
        raw_data: dict,
        id: Optional[int] = None,
        subject: Optional[str] = None,
        requester_id: Optional[int] = None,
        responder_id: Optional[str] = None,
        department_id: Optional[int] = None,
        group_id: Optional[int] = None,
        updated_at: Optional[str] = None,
        created_at: Optional[str] = None,
        priority: Optional[int] = None,
        requester_email: Optional[str] = None,
        due_by: Optional[str] = None,
        type: Optional[str] = None,
        category: Optional[str] = None,
        status: Optional[int] = None,
        tags: Optional[str] = None,
        source: Optional[int] = None,
        is_escalated: Optional[bool] = None,
        custom_fields: Optional[Dict[str, str]] = None,
        description: Optional[str] = None,
        description_text: Optional[str] = None,
        deleted: Optional[bool] = None,
    ):
        super(Ticket, self).__init__(raw_data)
        self.id = id
        self.subject = subject
        self.category = category
        self.requester_email = requester_email
        self.description = description
        self.description_text = description_text
        self.is_escalated = is_escalated
        self.deleted = deleted
        self.department_id = department_id
        self.priority = priority
        self.group_id = group_id
        self.requester_id = requester_id
        self.responder_id = responder_id
        self.updated_at = updated_at
        self.created_at = created_at
        self.due_by = due_by
        self.status = status
        self.type = type
        self.source = source
        self.tags = tags or []
        self.custom_fields = custom_fields or {}

        self.priority_name = MAPPED_TICKET_PRIORITIES.get(self.priority)
        self.status_name = MAPPED_TICKET_STATUSES.get(self.status)
        self.source_name = MAPPED_TICKET_SOURCES.get(self.source)

        try:
            self.updated_at_unix = convert_datetime_to_unix_time(
                datetime.strptime(self.updated_at, DATE_FORMAT)
            )
        except:
            self.updated_at_unix = 1

    def to_json(self):
        data = copy.deepcopy(self.raw_data)
        if self.priority_name:
            data["priority_name"] = self.priority_name
        if self.status_name:
            data["status_name"] = self.status_name
        if self.source_name:
            data["source_name"] = self.source_name

        return data

    def to_events(
        self,
        department_name: Optional[str] = None,
        agent_group_name: Optional[str] = None,
        responder_email: Optional[str] = None,
        responder_location_name: Optional[int] = None,
    ):
        """
        Converts the instance data to a list of event dictionaries.

        Args:
            department_name (Optional[str]): Name of the department.
            agent_group_name (Optional[str]): Name of the agent group.
            responder_email (Optional[str]): Email of the responder.
            responder_location_name (Optional[int]): Name of the responder's location.

        Returns:
            List[Dict[str, Optional[str]]]: A list containing a single event dictionary.
        """
        event = self.to_flat()

        event["priority_name"] = self.priority_name
        event["status_name"] = self.status_name
        event["source_name"] = self.source_name

        if department_name:
            event["department_name"] = department_name
        if agent_group_name:
            event["agent_group_name"] = agent_group_name
        if responder_email:
            event["responder_email"] = responder_email

        if responder_location_name is not None:
            event["responder_location_name"] = responder_location_name

        return [event]

    def to_csv(self):
        return {
            "ID": self.id,
            "Type": self.type,
            "Subject": self.subject,
            "Description": self.description_text,
            "Requester Email": self.requester_email,
            "Category": self.category,
            "Status": self.status_name or "",
            "Priority": self.priority_name or "",
            "Source": self.source_name or "",
            "Created Date": self.created_at,
            "Updated Date": self.updated_at,
            "Due Date": self.due_by,
            "Escalated": self.is_escalated,
            "Deleted": self.deleted,
        }

    def get_alert_info(
        self,
        alert_info,
        environment_common,
        department_name=None,
        agent_group_name=None,
        responder_email=None,
        responder_location_name=None,
    ):
        """
        Populates the alert_info object with ticket and environment details.

        Args:
            alert_info: The alert information object to populate.
            environment_common: An object to get environment details.
            department_name (Optional[str]): Name of the department.
            agent_group_name (Optional[str]): Name of the agent group.
            responder_email (Optional[str]): Email of the responder.
            responder_location_name (Optional[int]): Name of the responder's location.
        
        Returns:
            The populated alert_info object.
        """
        alert_info.environment = environment_common.get_environment(self.to_flat())
        alert_info.ticket_id = self.id
        alert_info.display_id = str(uuid.uuid4())
        alert_info.name = f"Freshservice ticket: {self.subject}"
        alert_info.device_vendor = DEVICE_VENDOR
        alert_info.device_product = DEVICE_PRODUCT
        alert_info.priority = TICKET_PRIORITY_TO_SIEM_SEVERITY.get(self.priority, -1)
        alert_info.rule_generator = f"Freshservice_{self.type}"
        alert_info.start_time = convert_datetime_to_unix_time(
            datetime.strptime(self.created_at, DATE_FORMAT)
        )
        alert_info.end_time = convert_datetime_to_unix_time(
            datetime.strptime(self.due_by, DATE_FORMAT)
        )

        alert_info.events = self.to_events(
            department_name, agent_group_name, responder_email, responder_location_name
        )

        return alert_info


class Department(BaseModel):
    """
    Freshservice Department
    """

    def __init__(
        self,
        raw_data: dict,
        id: Optional[int] = None,
        name: Optional[str] = None,
        description: Optional[str] = None,
        created_at: Optional[str] = None,
        updated_at: Optional[str] = None,
    ):
        super(Department, self).__init__(raw_data)
        self.description = description
        self.id = id
        self.name = name
        self.created_at = created_at
        self.updated_at = updated_at


class Location(BaseModel):
    """
    Freshservice Location
    """

    def __init__(
        self,
        raw_data: dict,
        id: Optional[int] = None,
        name: Optional[str] = None,
        created_at: Optional[str] = None,
        updated_at: Optional[str] = None,
    ):
        super(Location, self).__init__(raw_data)
        self.id = id
        self.name = name
        self.created_at = created_at
        self.updated_at = updated_at


class AgentGroup(BaseModel):
    """
    Freshservice Agent Group
    """

    def __init__(
        self,
        raw_data: dict,
        id: Optional[int] = None,
        name: Optional[str] = None,
        description: Optional[str] = None,
        created_at: Optional[str] = None,
        updated_at: Optional[str] = None,
        members: Optional[List[int]] = None,
    ):
        super(AgentGroup, self).__init__(raw_data)
        self.id = id
        self.name = name
        self.description = description
        self.created_at = created_at
        self.updated_at = updated_at
        self.members = members or []


class Role(BaseModel):
    """
    Freshservice Role
    """

    def __init__(
        self, raw_data: dict, id: Optional[int] = None, name: Optional[str] = None
    ):
        super(Role, self).__init__(raw_data)
        self.raw_data = raw_data
        self.id = id
        self.name = name


class Agent(BaseModel):
    """
    Freshservice Agent
    """

    def __init__(
        self,
        raw_data: dict,
        email: Optional[str] = None,
        department_ids: Optional[List[int]] = None,
        agent_id: Optional[int] = None,
        created_at: Optional[str] = None,
        updated_at: Optional[str] = None,
        group_ids: Optional[List[int]] = None,
        location_id: Optional[int] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        roles: Optional[List[Dict]] = None,
        active: Optional[bool] = None,
        occasional: Optional[bool] = None,
        custom_fields: Optional[dict] = None,
        last_login_at: Optional[str] = None,
        last_active_at: Optional[str] = None,
    ):
        super(Agent, self).__init__(raw_data)
        self.agent_id = agent_id
        self.email = email
        self.department_ids = department_ids or []
        self.location_id = location_id
        self.group_ids = group_ids or []
        self.created_at = created_at
        self.updated_at = updated_at
        self.first_name = first_name
        self.last_name = last_name
        self.roles = roles or []
        self.active = active
        self.occasional = occasional
        self.custom_fields = custom_fields or {}
        self.last_login_at = last_login_at
        self.last_active_at = last_active_at

    def as_csv(self):
        return {
            "ID": self.agent_id,
            "Email": self.email,
            "First Name": self.first_name,
            "Last Name": self.last_name,
            "Roles": ", ".join(self.raw_data.get("agent_role_names", [])),
            "Groups": ", ".join(self.raw_data.get("member_group_names", [])),
            "Departments": ", ".join(self.raw_data.get("department_names", [])),
            "Location": self.raw_data.get("location_name"),
            "Active": self.active,
            "Occasional": self.occasional,
            "Custom Fields": self.custom_fields,
            "Created Date": self.created_at,
            "Updated Date": self.updated_at,
            "Last Active Date": self.last_active_at,
            "Last Login Date": self.last_login_at,
        }


class TicketConversation(BaseModel):
    """
    Freshservice Ticket Conversation
    """

    def __init__(
        self,
        raw_data,
        conversation_id: Optional[int] = None,
        source: Optional[int] = None,
        body_text: Optional[str] = None,
        user_id: Optional[int] = None,
        private: Optional[bool] = None,
        from_email: Optional[str] = None,
        updated_at: Optional[str] = None,
        cc_emails: Optional[List[str]] = None,
        to_emails: Optional[List[str]] = None,
        bcc_emails: Optional[List[str]] = None,
    ):
        super(TicketConversation, self).__init__(raw_data)
        self.user_id = user_id
        self.updated_at = updated_at
        self.conversation_id = conversation_id
        self.source = source
        self.private = private
        self.body_text = body_text
        self.from_email = from_email
        self.bcc_emails = bcc_emails or []
        self.cc_emails = cc_emails or []
        self.to_emails = to_emails or []

        self.user_email = None
        self.source_name = MAPPED_CONVERSATION_SOURCE_TYPES.get(self.source)

        try:
            self.updated_at_unix = convert_datetime_to_unix_time(
                datetime.strptime(self.updated_at, DATE_FORMAT)
            )
        except:
            self.updated_at_unix = 1

    def set_user_email(self, user_email: str):
        self.user_email = user_email

    def to_json(self):
        data = copy.deepcopy(self.raw_data)
        if self.user_email:
            data["user_email"] = self.user_email
        if self.source_name:
            data["source_name"] = self.source_name
        if self.from_email:
            try:
                match = re.search("<(.*)>", self.from_email)
                if match:
                    data["from_email"] = match.group(1)
            except:
                pass

        return data

    def to_csv(self):
        return {
            "ID": self.user_id,
            "Type": self.source_name,
            "Visibility": (
                "Private"
                if isinstance(self.private, bool) and self.private
                else "Public"
            ),
            "User Email": self.user_email or "",
            "Text": self.body_text or "",
            "From Email": self.from_email or "",
            "To Email": CSV_TABLE_DELIMITER.join(self.to_emails),
            "CC Email": CSV_TABLE_DELIMITER.join(self.cc_emails),
            "BCC Email": CSV_TABLE_DELIMITER.join(self.bcc_emails),
        }


class Requester(BaseModel):
    """
    Freshservice Requester
    """

    def __init__(
        self,
        raw_data: dict,
        requester_id: Optional[int] = None,
        primary_email: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        department_ids: Optional[List[int]] = None,
        location_id: Optional[int] = None,
        active: Optional[bool] = None,
        custom_fields: Optional[dict] = None,
        created_at: Optional[str] = None,
        updated_at: Optional[str] = None,
    ):
        super(Requester, self).__init__(raw_data)
        self.raw_data = raw_data
        self.requester_id = requester_id
        self.primary_email = primary_email
        self.first_name = first_name
        self.last_name = last_name
        self.location_id = location_id
        self.active = active
        self.created_at = created_at
        self.updated_at = updated_at
        self.department_ids = department_ids or []
        self.custom_fields = custom_fields or {}

        self.location_name = None
        self.department_names = []

    def set_location_name(self, location_name: str):
        self.location_name = location_name

    def set_department_names(self, department_names: List[str]):
        self.department_names = department_names

    def to_json(self):
        data = copy.deepcopy(self.raw_data)
        if self.location_name:
            data["location_name"] = self.location_name
        if self.department_names:
            data["department_names"] = self.department_names

        return data

    def as_csv(self):
        return {
            "ID": self.requester_id,
            "Email": self.primary_email,
            "First Name": self.first_name or "",
            "Last Name": self.last_name or "",
            "Departments": ", ".join(self.raw_data.get("department_names", [])),
            "Location": self.raw_data.get("location_name"),
            "Active": self.active,
            "Custom Fields": self.custom_fields,
            "Created Date": self.created_at,
            "Updated Date": self.updated_at,
        }


class TicketTimeEntry(BaseModel):
    """
    Ticket Time Entry
    """

    def __init__(
        self,
        raw_data: dict,
        agent_id: Optional[int] = None,
        time_entry_id: Optional[int] = None,
        note: Optional[str] = None,
        billable: Optional[bool] = None,
        time_spent: Optional[str] = None,
        task_id: Optional[int] = None,
        custom_fields: Optional[dict] = None,
        timer_running: Optional[bool] = None,
        created_at: Optional[str] = None,
        updated_at: Optional[str] = None,
        start_time: Optional[str] = None,
        executed_at: Optional[str] = None,
    ):
        super(TicketTimeEntry, self).__init__(raw_data)
        self.agent_id = agent_id
        self.time_entry_id = time_entry_id
        self.note = note
        self.billable = billable
        self.time_spent = time_spent
        self.task_id = task_id
        self.timer_running = timer_running
        self.created_at = created_at
        self.updated_at = updated_at
        self.start_time = start_time
        self.executed_at = executed_at
        self.custom_fields = custom_fields or {}

        self.agent_email = None

    def set_agent_email(self, agent_email: str):
        self.agent_email = agent_email

    def as_csv(self):
        return {
            "Time Entry ID": self.time_entry_id,
            "Agent Email": self.agent_email or "",
            "Note": self.note or "",
            "Billable": self.billable,
            "Time Spent": f"{self.time_spent} HRS",
            "Task ID": self.task_id or "",
            "Custom Fields": self.custom_fields,
            "Timer Running": self.timer_running,
            "Created Time": self.created_at,
            "Updated Time": self.updated_at,
            "Start Time": self.start_time,
            "Executed Time": self.executed_at,
        }
