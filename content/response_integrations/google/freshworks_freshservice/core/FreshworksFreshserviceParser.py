from __future__ import annotations
from .consts import NEW_LINE
from .datamodels import (
    Ticket,
    TicketConversation,
    Department,
    Location,
    Agent,
    AgentGroup,
    Role,
    Requester,
    TicketTimeEntry,
)


class FreshworksFreshserviceParser:
    """
    Freshworks Freshservice Transformation Layer
    """

    @staticmethod
    def get_response_errors(response: dict):
        error_messages = []
        description = response.get("description", "")
        error_codes = (
            [response.get("code")]
            if response.get("code") and isinstance(response.get("code"), str)
            else []
        )

        for error in response.get("errors", []):
            error_messages.append(
                NEW_LINE.join(f" {key}: {value}" for key, value in error.items())
            )
            if error.get("code"):
                error_codes.append(error.get("code"))

        return description, error_messages, error_codes, bool(error_messages)

    @staticmethod
    def get_pagination_link_header(headers: dict):
        return headers.get("Link")

    @staticmethod
    def build_ticket_obj_list(raw_data: dict):
        return [
            FreshworksFreshserviceParser.build_ticket_obj(raw_ticket)
            for raw_ticket in raw_data.get("tickets", [])
        ]

    @staticmethod
    def build_updated_ticket_obj(raw_data: dict):
        return FreshworksFreshserviceParser.build_ticket_obj(raw_data.get("ticket", {}))

    @staticmethod
    def build_created_ticket_obj(raw_data: dict):
        return FreshworksFreshserviceParser.build_ticket_obj(raw_data.get("ticket", {}))

    @staticmethod
    def build_get_ticket_obj(raw_data: dict):
        return FreshworksFreshserviceParser.build_ticket_obj(raw_data.get("ticket", {}))

    @staticmethod
    def build_ticket_obj(raw_data: dict):
        return Ticket(
            raw_data=raw_data,
            id=raw_data.get("id"),
            priority=raw_data.get("priority"),
            requester_email=raw_data.get("requester", {}).get("email"),
            category=raw_data.get("category"),
            is_escalated=raw_data.get("is_escalated"),
            deleted=raw_data.get("deleted"),
            subject=raw_data.get("subject"),
            description=raw_data.get("description"),
            description_text=raw_data.get("description_text"),
            requester_id=raw_data.get("responder_id"),
            responder_id=raw_data.get("responder_id"),
            department_id=raw_data.get("department_id"),
            group_id=raw_data.get("group_id"),
            updated_at=raw_data.get("updated_at"),
            created_at=raw_data.get("created_at"),
            due_by=raw_data.get("due_by"),
            type=raw_data.get("type"),
            source=raw_data.get("source"),
            status=raw_data.get("status"),
            tags=raw_data.get("tags", []),
            custom_fields=raw_data.get("custom_fields", {}),
        )

    @staticmethod
    def build_department_obj_list(raw_data: dict):
        return [
            FreshworksFreshserviceParser.build_department_obj(raw_department)
            for raw_department in raw_data.get("departments", [])
        ]

    @staticmethod
    def build_department_obj(raw_department: dict):
        return Department(
            raw_data=raw_department,
            name=raw_department.get("name"),
            description=raw_department.get("description"),
            id=raw_department.get("id"),
            created_at=raw_department.get("created_at"),
            updated_at=raw_department.get("updated_at"),
        )

    @staticmethod
    def build_agent_roles_obj_list(raw_data: dict):
        return [
            FreshworksFreshserviceParser.build_agent_role_obj(raw_role)
            for raw_role in raw_data.get("roles", [])
        ]

    @staticmethod
    def build_agent_role_obj(raw_role: dict):
        return Role(raw_data=raw_role, name=raw_role.get("name"), id=raw_role.get("id"))

    @staticmethod
    def build_location_obj_list(raw_data: dict):
        return [
            FreshworksFreshserviceParser.build_location_obj(raw_location)
            for raw_location in raw_data.get("locations", [])
        ]

    @staticmethod
    def build_location_obj(raw_location: dict):
        return Location(
            raw_data=raw_location,
            id=raw_location.get("id"),
            name=raw_location.get("name"),
            created_at=raw_location.get("created_at"),
            updated_at=raw_location.get("updated_at"),
        )

    @staticmethod
    def build_agent_group_obj_list(raw_data: dict):
        return [
            FreshworksFreshserviceParser.build_agent_group_obj(raw_group)
            for raw_group in raw_data.get("groups", [])
        ]

    @staticmethod
    def build_agent_group_obj(raw_group: dict):
        return AgentGroup(
            raw_data=raw_group,
            id=raw_group.get("id"),
            name=raw_group.get("name"),
            description=raw_group.get("description"),
            created_at=raw_group.get("created_at"),
            updated_at=raw_group.get("updated_at"),
        )

    @staticmethod
    def build_agent_obj_list(raw_data: dict):
        return [
            FreshworksFreshserviceParser.build_agent_obj(raw_group)
            for raw_group in raw_data.get("agents", [])
        ]

    @staticmethod
    def build_agent_obj(raw_agent: dict):
        return Agent(
            raw_data=raw_agent,
            agent_id=raw_agent.get("id"),
            email=raw_agent.get("email"),
            department_ids=raw_agent.get("department_ids", []),
            location_id=raw_agent.get("location_id"),
            created_at=raw_agent.get("created_at"),
            updated_at=raw_agent.get("updated_at"),
            group_ids=raw_agent.get("group_ids", []),
            first_name=raw_agent.get("first_name", ""),
            last_name=raw_agent.get("last_name", ""),
            roles=raw_agent.get("roles", []),
            active=raw_agent.get("active"),
            occasional=raw_agent.get("occasional"),
            custom_fields=raw_agent.get("custom_fields", {}),
            last_login_at=raw_agent.get("last_login_at", ""),
            last_active_at=raw_agent.get("last_active_at", ""),
        )

    @staticmethod
    def build_ticket_conversations_obj_list(raw_data: dict):
        return [
            FreshworksFreshserviceParser.build_ticket_conversation_obj(raw_conversation)
            for raw_conversation in raw_data.get("conversations", [])
        ]

    @staticmethod
    def build_ticket_conversation_obj(raw_conversation: dict):
        return TicketConversation(
            raw_data=raw_conversation,
            user_id=raw_conversation.get("user_id"),
            conversation_id=raw_conversation.get("id"),
            updated_at=raw_conversation.get("updated_at"),
            source=raw_conversation.get("source"),
            private=raw_conversation.get("private"),
            body_text=raw_conversation.get("body_text"),
            from_email=raw_conversation.get("from_email"),
            to_emails=raw_conversation.get("to_emails", []),
            cc_emails=raw_conversation.get("cc_emails", []),
            bcc_emails=raw_conversation.get("bcc_emails", []),
        )

    @staticmethod
    def build_requester_obj_list(raw_data: dict):
        return [
            FreshworksFreshserviceParser.build_requester_obj(raw_requester)
            for raw_requester in raw_data.get("requesters", [])
        ]

    @staticmethod
    def build_created_requester_obj(raw_data: dict):
        return FreshworksFreshserviceParser.build_requester_obj(
            raw_data.get("requester", {})
        )

    @staticmethod
    def build_updated_requester_obj(raw_data: dict):
        return FreshworksFreshserviceParser.build_requester_obj(
            raw_data.get("requester", {})
        )

    @staticmethod
    def build_requester_obj(raw_requester: dict):
        return Requester(
            raw_data=raw_requester,
            requester_id=raw_requester.get("id"),
            primary_email=raw_requester.get("primary_email"),
            first_name=raw_requester.get("first_name"),
            last_name=raw_requester.get("last_name"),
            department_ids=raw_requester.get("department_ids", []),
            location_id=raw_requester.get("location_id"),
            active=raw_requester.get("active"),
            custom_fields=raw_requester.get("custom_fields", {}),
            created_at=raw_requester.get("created_at"),
            updated_at=raw_requester.get("updated_at"),
        )

    @staticmethod
    def build_ticket_reply_conversation_obj(raw_conversation: dict):
        return FreshworksFreshserviceParser.build_ticket_conversation_obj(
            raw_conversation.get("conversation", {})
        )

    @staticmethod
    def build_ticket_note_conversation_obj(raw_conversation: dict):
        return FreshworksFreshserviceParser.build_ticket_conversation_obj(
            raw_conversation.get("conversation", {})
        )

    @staticmethod
    def build_ticket_time_entry_obj_list(raw_data: dict):
        return [
            FreshworksFreshserviceParser.build_ticket_time_entry_obj(time_entry)
            for time_entry in raw_data.get("time_entries", [])
        ]

    @staticmethod
    def build_added_ticket_time_entry_obj(raw_data: dict):
        return FreshworksFreshserviceParser.build_ticket_time_entry_obj(
            raw_data.get("time_entry", {})
        )

    @staticmethod
    def build_updated_ticket_time_entry_obj(raw_data: dict):
        return FreshworksFreshserviceParser.build_ticket_time_entry_obj(
            raw_data.get("time_entry", {})
        )

    @staticmethod
    def build_ticket_time_entry_obj(raw_time_entry):
        return TicketTimeEntry(
            raw_data=raw_time_entry,
            agent_id=raw_time_entry.get("agent_id"),
            time_entry_id=raw_time_entry.get("id"),
            note=raw_time_entry.get("note"),
            time_spent=raw_time_entry.get("time_spent"),
            billable=raw_time_entry.get("billable"),
            task_id=raw_time_entry.get("task_id"),
            timer_running=raw_time_entry.get("timer_running"),
            created_at=raw_time_entry.get("created_at"),
            updated_at=raw_time_entry.get("updated_at"),
            start_time=raw_time_entry.get("start_time"),
            executed_at=raw_time_entry.get("executed_at"),
            custom_fields=raw_time_entry.get("custom_fields", {}),
        )
