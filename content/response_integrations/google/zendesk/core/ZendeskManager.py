# ==============================================================================
# title           :ZendeskManager.py
# description     :This Module contain all Zendesk operations functionality
# author          :zdemoniac@gmail.com
# date            :07-02-18
# python_version  :2.7
# libraries       :
# requirements    :
# product_version : v2 API
# Doc             : https://developer.zendesk.com/rest_api/docs/core/introduction#the-api
# ==============================================================================

# =====================================
#              IMPORTS                #
# =====================================
from __future__ import annotations

import base64
import requests
from requests import Response

# =====================================
#             CONSTANTS               #
# =====================================
BASE_URL = "{0}/api/v2"
HEADERS = {"Content-Type": "application/json", "Accept": "application/json"}

NOT_FOUND_ERROR = "Not found"
# =====================================
#              CLASSES                #
# =====================================


class ZendeskManagerError(Exception):
    """
    General Exception for Zendesk manager
    """

    pass


class ZendeskManager:
    """Responsible for all Zendesk system operations functionality.
    This API is rate limited. Allow a certain number of requests per minute
    depending on user plan and the endpoint.
    """

    def __init__(self, email, api_token, server_address):
        self.url = BASE_URL.format(server_address)

        self.session = requests.session()
        # This is an SSL-only API
        self.session.verify = False
        self.session.headers = HEADERS
        # Create token and insert it to the header.
        self.session.headers.update(
            {
                "Authorization": "Basic {0}".format(
                    base64.b64encode(
                        f"{email}/token:{api_token}".encode("utf-8")
                    ).decode("utf-8")
                )
            }
        )

    def test_connectivity(self) -> bool:
        """Validates connectivity

        Returns: A boolean value if connectivity is OK
        """
        tickets = self.get_tickets()
        if tickets:
            return True
        return False

    def get_tickets(self) -> dict:
        """Get all tickets

        Returns: It returns all the tickets
        """
        # Returns a maximum of 100 tickets per page.
        # Tickets are ordered chronologically by created date, from oldest to newest.
        url = f'{self.url}/{"tickets"}.json'
        r = self.session.get(url)
        return self.validate_response(r)

    def get_ticket_details(self, ticket_id: str) -> dict:
        """Get ticket details

        Args:
            ticket_id: The ticket ID

        Returns: It returns the ticket details
        """
        url = f'{self.url}/{"tickets"}/{ticket_id}.json'
        r = self.session.get(url)
        return self.validate_response(r)

    def get_user_id_by_name(self, user_name: str) -> int:
        """Retrieve user id

        Args:
            user_name: A user full name (Case sensitive)

        Returns: It returns the user id
        """
        url = f"{self.url}/users.json"
        users_list = self.session.get(url)
        users_list = self.validate_response(users_list)
        if users_list:
            for user in users_list["users"]:
                if user["name"] == user_name:
                    return user["id"]
        raise ZendeskManagerError(f"User {user_name} does not exist in Zendesk.")

    def get_group_id_by_name(self, group_name: str) -> int:
        """Retrieve group id

        Args:
            group_name:  group name of the Assignment Group

        Returns: group id
        """
        url = f"{self.url}/groups.json"
        groups_list = self.session.get(url)
        groups_list = self.validate_response(groups_list)
        if groups_list:
            for group in groups_list["groups"]:
                if group["name"] == group_name:
                    return group["id"]
        raise ZendeskManagerError(f"Group {group_name} does not exist in Zendesk.")

    def get_users_email_addresses(self) -> list:
        """Get all users email addresses

        Returns: A list of users email addresses
        """
        url = f"{self.url}/users.json"
        params = {"page[size]": 100}
        response = self.session.get(url, params=params)
        json_response = self.validate_response(response)
        users = json_response.get("users", [])
        has_more = json_response.get("meta", {}).get("has_more", False)
        cursor = json_response.get("meta", {}).get("after_cursor", "")

        while has_more:
            params.update({"page[after]": cursor})

            response = self.session.get(url, params=params)
            json_response = self.validate_response(response)
            has_more = json_response.get("meta", {}).get("has_more", False)
            cursor = json_response.get("meta", {}).get("after_cursor", "")
            users.extend(json_response.get("users", []))

        return [user["email"] for user in users] if users else []

    def create_ticket(
        self,
        subject: str,
        description: str,
        assigned_to: str | None = None,
        assignment_group: str | None = None,
        priority: str | None = None,
        ticket_type: str | None = None,
        tags: list | None = None,
        internal_note: bool = False,
        email_ccs: list | None = None,
    ) -> dict:
        """Create a "ticket" object that specifies the ticket properties.

        Args:
            subject:  The subject of the ticket
            description: The initial comment
            assigned_to: user full name
            assignment_group: group name
            priority: Allowed values are urgent, high, normal, or low
            ticket_type: Allowed values are problem, incident, question, or task
            tags: An list of tags to add to the ticket
            internal_note: Specify whether the ticket is internal or not
            email_ccs: A list of emails to send the notification to

        Returns: A ticket object and an audit object with an events array that lists
            all the updates made to the new ticket.
        """
        url = f'{self.url}/{"tickets"}.json'

        # The only required property is "comment".
        ticket_data = {
            "ticket": {
                "subject": subject,
                "comment": {"body": description},
                "status": "open",
            }
        }

        if assigned_to:
            # Convert to the numeric ID of the agent to assign the ticket to.
            assigne_id = self.get_user_id_by_name(assigned_to)
            ticket_data["ticket"]["assignee_id"] = assigne_id

        if assignment_group:
            # Convert to the numeric ID of the agent to assign the ticket to.
            group_id = self.get_group_id_by_name(assignment_group)
            ticket_data["ticket"]["group_id"] = group_id

        if priority:
            ticket_data["ticket"]["priority"] = priority

        if ticket_type:
            ticket_data["ticket"]["type"] = ticket_type

        if tags:
            ticket_data["ticket"]["tags"] = tags

        if not internal_note:
            ticket_data["ticket"]["comment"]["public"] = internal_note

        if email_ccs:
            ticket_data["ticket"]["email_ccs"] = []
            for email in email_ccs:
                ticket_data["ticket"]["email_ccs"].append(
                    {"user_email": email, "action": "put"}
                )

        r = self.session.post(url, json=ticket_data)
        return self.validate_response(r)

    def get_ticket_tags(self, ticket_id: str) -> list:
        """Get tickets that belong to specific tag

        Args:
            ticket_id: Ticket number

        Returns: A list of ticket tags
        """
        url = f'{self.url}/{"tickets"}/{ticket_id}/{"tags"}.json'
        r = self.session.get(url)
        return self.validate_response(r)["tags"]

    def update_ticket(
        self,
        ticket_id: str,
        subject: str | None = None,
        assigned_to: str | None = None,
        assignment_group: str | None = None,
        priority: str | None = None,
        ticket_type: str | None = None,
        tag: str | None = None,
        status: str | None = None,
    ) -> dict | None:
        """Update  existing ticket details

        Args:
            ticket_id: ticket number
            subject: The subject of the ticket
            assigned_to: user full name
            assignment_group: group name
            priority: Allowed values are urgent, high, normal, or low
            ticket_type: Allowed values are problem, incident, question, or task
            tag: A tag to add to the ticket.
            status: The state of the ticket. Possible values: "new", "open",
                "pending", "hold", "solved", "closed"

        Returns: A ticket object and an audit object with an events array that lists
            all the updates.
        """
        # The PUT request takes one parameter, a ticket object
        ticket_data = self.get_ticket_details(ticket_id)

        if ticket_data:

            if subject:
                ticket_data["ticket"]["raw_subject"] = subject

            if assigned_to:
                # Convert to the numeric ID of the agent to assign the ticket to.
                assigne_id = self.get_user_id_by_name(assigned_to)
                ticket_data["ticket"]["assignee_id"] = assigne_id

            if assignment_group:
                # Convert to the numeric ID of the agent to assign the ticket to.
                group_id = self.get_group_id_by_name(assignment_group)
                ticket_data["ticket"]["group_id"] = group_id

            if priority:
                ticket_data["ticket"]["priority"] = priority

            if ticket_type:
                ticket_data["ticket"]["type"] = ticket_type

            if tag:
                tags = self.get_ticket_tags(ticket_id)
                tags.append(tag)
                ticket_data["ticket"]["tags"] = tags

            if status:
                ticket_data["ticket"]["status"] = status

            url = f'{self.url}/{"tickets"}/{ticket_id}.json'
            r = self.session.put(url, json=ticket_data)
            return self.validate_response(r)

        return None

    def get_agents(self) -> dict | None:
        """Get list of all agents (Include admin users)

        Returns: All agents
        """
        # Administrators have all the abilities of agents
        url = f"{self.url}/users.json"
        agents_list = self.session.get(url, params={"role[]": ["agent", "admin"]})
        return self.validate_response(agents_list)

    def get_ticket_comments(self, ticket_id: str) -> dict | None:
        """Ticket comments represent the conversation between requesters,
        collaborators, and agents.

        Args:
            ticket_id: A ticket number

        Returns: All comments for a ticket
        """
        url = f'{self.url}/{"tickets"}/{ticket_id}/{"comments"}.json'
        r = self.session.get(url)
        return self.validate_response(r)

    def add_comment_to_ticket(
        self,
        ticket_id: str,
        comment_body: str | None = None,
        author_name: str | None = None,
        internal_note: bool = True
    ) -> dict | None:
        """Add comment to ticket
        Ticket comments represent the conversation between requesters, collaborators,
        and agents. Comments can be public or private.

        Args:
            ticket_id: A ticket number
            comment_body: The comment to add to the conversation
            author_name: The full name of the comment author.
            internal_note: True if a public comment; false if an internal note.

        Returns: A ticket object and an audit object with an events array that lists
            all the updates.
        """
        # The PUT request takes one parameter, a ticket object
        ticket_data = self.get_ticket_details(ticket_id)

        if ticket_data:
            # Add comment field - Ticket comments are represented as JSON objects
            ticket_data["ticket"].update({"comment": {}})

            if comment_body:
                ticket_data["ticket"]["comment"]["body"] = comment_body

            if author_name:
                # Convert to the numeric ID of the comment author.
                author_id = self.get_user_id_by_name(author_name)
                ticket_data["ticket"]["comment"]["author_id"] = author_id

            if not internal_note:
                ticket_data["ticket"]["comment"]["public"] = internal_note

            url = f'{self.url}/{"tickets"}/{ticket_id}.json'
            r = self.session.put(url, json=ticket_data)
            return self.validate_response(r)

        raise ZendeskManagerError(
            f"Failed to add comment to ticket with ID: {ticket_id}."
        )

    def get_attachments_from_ticket(self, ticket_id: str) -> list:
        """Get attachments from ticket

        Args:
            ticket_id: A ticket number

        Returns: A list of file contents
        """
        # Get ticket details
        ticket_comments = self.session.get(
            f"{self.url}/tickets/{ticket_id}/comments.json"
        )
        attachments = []
        ticket_comments = self.validate_response(ticket_comments)
        if ticket_comments:
            for comment in ticket_comments["comments"]:
                if comment["attachments"]:
                    for attachment in comment["attachments"]:
                        file_content = self.session.get(
                            attachment["content_url"]
                        ).content
                        attachments.append({attachment["file_name"]: file_content})
        return attachments

    def search_tickets(self, query: str) -> dict:
        """Search ticket using filters

        Args:
            query: A search string. For example: 'type:ticket status:pending'

        Returns: Queries are represented as JSON
        """
        url = f'{self.url}/{"search"}.json'
        r = self.session.get(url, params={"query": query})
        return self.validate_response(r)

    def get_macro_id_by_name(self, macro_name: str) -> str:
        """Get macro id by macro title

        Args:
            macro_name: macro title (Case sensitive)

        Returns: macro id
        """
        url = f"{self.url}/macros.json"
        r = self.session.get(url)
        macros = self.validate_response(r).get("macros")
        if macros:
            for macro in macros:
                if macro_name == macro["title"]:
                    return str(macro["id"])
        raise ZendeskManagerError(f"{macro_name} Macro does not exist.")

    def apply_macro_on_ticket(self, ticket_id: str, macro_title: str) -> dict | None:
        """Apply macro on specific ticket

        Args:
            ticket_id: A ticket id of the Ticket
            macro_title: The macro title that needs to be applied

        Returns: A full ticket as it would be after applying the macro to the ticket.
        """
        # Get macro id by macro name
        macro_id = self.get_macro_id_by_name(macro_title)
        if macro_id:
            url = f'{self.url}/{"tickets"}/{ticket_id}/{"macros"}/{macro_id}/apply.json'
            r = self.session.get(url)
            ticket_new_data = self.validate_response(r)

            # Update ticket with the response data because this request doesn't actually change the ticket.
            url = f'{self.url}/{"tickets"}/{ticket_id}.json'
            res = self.session.put(url, json=ticket_new_data["result"])
            return self.validate_response(res)
        raise ZendeskManagerError(f"{macro_title} Macro does not exist.")

    @staticmethod
    def validate_response(response: Response) -> dict | None:
        """Validate an HTTP response.

        Args:
            response: HTTP response object

        Returns: A response dict or None if validation fails.
        """
        try:
            if NOT_FOUND_ERROR in response.text and response.status_code == 404:
                return None
            response.raise_for_status()
        except requests.HTTPError as err:
            raise ZendeskManagerError(f"HTTP Error: {err}")
        return response.json()
