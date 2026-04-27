# ============================================================================#
# title           :FreshworksFreshserviceManager.py
# description     :This Module contain all Freshworks Freshservice operations functionality
# author          :gabriel.munits@siemplify.co
# date            :07-07-2021
# python_version  :3.7
# product_version :1.0
# ============================================================================#
from __future__ import annotations
import os
from copy import deepcopy
from typing import Optional, List, Dict
from urllib.parse import urljoin

import requests
from requests import Session

from .FreshworksFreshserviceParser import FreshworksFreshserviceParser
from soar_sdk.SiemplifyLogger import SiemplifyLogger
from soar_sdk.SiemplifyBase import SiemplifyBase
from TIPCommon import filter_old_alerts
from .consts import (
    INTEGRATION_DISPLAY_NAME,
    API_LIMIT_ERROR,
    FORBIDDEN_CLIENT_ERROR,
    DOUBLE_NEW_LINE,
    INPUT_VALIDATION_ERRORS,
    AUTHORIZATION_ERRORS,
    NOT_FOUND_ERROR,
    AGENT_STATE_ALL,
    METHOD_NOT_ALLOWED_ERROR,
    DUPLICATE_VALUE,
)
from .datamodels import (
    Ticket,
    TicketConversation,
    TicketTimeEntry,
    Department,
    Location,
    AgentGroup,
    Agent,
    Role,
    Requester,
)
from .exceptions import (
    FreshworksFreshserviceManagerError,
    FreshworksFreshserviceAPILimitError,
    FreshworksFreshserviceAuthorizationError,
    FreshworksFreshserviceValidationError,
    FreshworksFreshserviceNotFoundError,
    FreshworksFreshserviceMethodNotAllowedError,
    FreshworksFreshserviceDuplicateValueError,
)
from .utils import remove_none_dictionary_values


# ============================= CONSTS ===================================== #

ENDPOINTS = {
    "ping": "/api/v2/tickets",
    "list-tickets": "/api/v2/tickets",
    "list-departments": "/api/v2/departments",
    "list-locations": "/api/v2/locations",
    "list-agent-groups": "/api/v2/groups",
    "list-agents": "/api/v2/agents",
    "create-ticket": "/api/v2/tickets",
    "get-ticket": "/api/v2/tickets/{ticket_id}",
    "update-ticket": "/api/v2/tickets/{ticket_id}",
    "list-agent-roles": "/api/v2/roles/",
    "create-agent": "/api/v2/agents",
    "list-ticket-conversations": "/api/v2/tickets/{ticket_id}/conversations",
    "list-requesters": "/api/v2/requesters",
    "add-ticket-reply": "/api/v2/tickets/{ticket_id}/reply",
    "add-ticket-note": "/api/v2/tickets/{ticket_id}/notes",
    "update-agent": "/api/v2/agents/{agent_id}",
    "deactivate-agent": "/api/v2/agents/{agent_id}",
    "update-requester": "/api/v2/requesters/{requester_id}",
    "create-requester": "/api/v2/requesters",
    "deactivate-requester": "/api/v2/requesters/{requester_id}",
    "list-ticket-time-entries": "/api/v2/tickets/{ticket_id}/time_entries",
    "add-ticket-time-entry": "/api/v2/tickets/{ticket_id}/time_entries",
    "update-ticket-time-entry": (
        "/api/v2/tickets/{ticket_id}/time_entries/{time_entry_id}"
    ),
    "delete-ticket-time-entry": (
        "/api/v2/tickets/{ticket_id}/time_entries/{time_entry_id}"
    ),
}

HEADERS = {"Content-Type": "application/json"}


# ============================= CLASSES ===================================== #


class FreshworksFreshserviceManager:
    """
    Freshworks Freshservice Manager
    """

    def __init__(
        self,
        api_root: str,
        api_key: str,
        verify_ssl: bool,
        siemplify: SiemplifyBase,
        force_test_connectivity: Optional[bool] = False,
    ):
        self._api_root: str = api_root[:-1] if api_root.endswith("/") else api_root
        self._session: Session = requests.Session()
        self._session.verify = verify_ssl
        self._session.headers = deepcopy(HEADERS)
        self._session.auth = (api_key, ":X")

        self._parser: FreshworksFreshserviceParser = FreshworksFreshserviceParser()
        self._siemplify = siemplify
        self._siemplify_logger: SiemplifyLogger = self._siemplify.LOGGER

        if force_test_connectivity:
            self.test_connectivity()

    def _get_full_url(self, url_key: str, **kwargs) -> str:
        """
        Get full url from url key.
        :param url_id: {str} The key of url
        :param kwargs: {dict} Key value arguments passed for string formatting
        :return: {str} The full url
        """
        return urljoin(self._api_root, ENDPOINTS[url_key].format(**kwargs))

    @staticmethod
    def validate_response(
        response, error_msg="An error occurred", parse_response_error_message=True
    ):
        """
        Validate a response
        :param response: {requests.Response} The response
        :param parse_response_error_message: {bool} True if exception messages should be parsed from a bad response, otherwise display raw exception message from the API
        :param error_msg: {str} The error message to display on failure
            raise FreshworksFreshserviceManagerError exception if failed to validate response
        """
        try:
            if response.status_code == API_LIMIT_ERROR:
                raise FreshworksFreshserviceAPILimitError(
                    "Reached API request limitation"
                )

            response.raise_for_status()

        except requests.HTTPError as error:
            try:
                if response.status_code == NOT_FOUND_ERROR:
                    raise FreshworksFreshserviceNotFoundError(
                        f"{error_msg}: {error} {response.content}"
                    ) from None

                response.json()
                description, error_messages, error_codes, parsed_successfully = (
                    FreshworksFreshserviceParser.get_response_errors(response.json())
                )

                if parse_response_error_message:
                    if parsed_successfully:
                        error_message = (
                            f"{error_msg}: {error} "
                            f"{description + '!' if description else ''}"
                            f" Errors: \n{DOUBLE_NEW_LINE.join(error_messages)}"
                        )
                    else:
                        error_message = (
                            f"{error_msg}: {error} "
                            f"{description + '!' if description else ''}"
                            " Reason: "
                            f"{response.json().get('message', response.content)}"
                        )
                else:
                    error_message = f"{response.content}"

                if (
                    any(error in error_codes for error in AUTHORIZATION_ERRORS)
                    or response.status_code == FORBIDDEN_CLIENT_ERROR
                ):  # Raise access denied error
                    raise FreshworksFreshserviceAuthorizationError(error_message)

                if any(
                    error in error_codes for error in INPUT_VALIDATION_ERRORS
                ):  # Added the code "invalid_size to the validation check
                    raise FreshworksFreshserviceValidationError(error_message)

                if any(error for error in error_codes if error == DUPLICATE_VALUE):
                    raise FreshworksFreshserviceDuplicateValueError(error_message)

                if response.status_code == METHOD_NOT_ALLOWED_ERROR:
                    raise FreshworksFreshserviceMethodNotAllowedError(
                        response.json().get("message", response.content)
                    ) from error

                raise FreshworksFreshserviceManagerError(error_message)
            except (
                FreshworksFreshserviceNotFoundError,
                FreshworksFreshserviceMethodNotAllowedError,
                FreshworksFreshserviceDuplicateValueError,
            ):
                raise
            except (
                FreshworksFreshserviceManagerError,
                FreshworksFreshserviceAuthorizationError,
                FreshworksFreshserviceValidationError,
            ):
                raise
            except:
                raise FreshworksFreshserviceManagerError(
                    f"{error_msg}: {error} {response.content}"
                )

    def test_connectivity(self):
        """
        Test connectivity with Freshworks Freshservice server
            raise Exception if failed to test connectivity
        """
        response = self._session.get(
            self._get_full_url("ping"), params={"page": 1, "per_page": 1}
        )
        self.validate_response(
            response,
            error_msg=f"Failed to test connectivity with {INTEGRATION_DISPLAY_NAME}",
        )

    def _paginate_results(
        self,
        method,
        url,
        parser_method,
        params=None,
        body=None,
        limit=None,
        existing_ids=None,
        ids_attribute_to_filter=None,
        err_msg="Unable to get results",
        page_size=100,
        start_page=1,
    ):
        """
        Paginate the results
        :param method: {str} The method of the request (GET, POST, PUT, DELETE, PATCH)
        :param url: {str} The url to send request to
        :param parser_method: {str} The name of parser method to build the result
        :param params: {dict} The params of the request
        :param body: {dict} The json payload of the request
        :param limit: {int} The limit of the results to fetch
        :param err_msg: {str} The message to display on error
        :param existing_ids: {[str]} List of existing ids to filter. If provided, ids_attribute_to_filter must also be provided
        :param ids_attribute_to_filter: {str} Attribute of item ids to filter
        :param page_size: {int} Items per page
        :param start_page: {int} Number of the first page to start pagination from
        :return: {list} List of results
        """
        params = params or {}
        page_number = start_page
        request_url = url
        params["per_page"] = page_size
        params.update({"page": page_number})

        next_pagination_link = None
        results = []

        while True:
            if next_pagination_link:
                if limit and len(results) >= limit:
                    break
                params.update({"page": params["page"] + 1})

            response = self._session.request(
                method, request_url, params=params, json=body
            )
            next_pagination_link = getattr(self._parser, "get_pagination_link_header")(
                response.headers
            )

            self.validate_response(response, err_msg)
            current_items = getattr(self._parser, parser_method)(response.json())

            if existing_ids and ids_attribute_to_filter:
                results.extend(
                    filter_old_alerts(
                        self._siemplify,
                        current_items,
                        existing_ids,
                        ids_attribute_to_filter,
                    )
                )
            else:
                results.extend(current_items)

            if len(current_items) < page_size:
                break

            if not next_pagination_link:
                break

        return results[:limit] if limit else results

    def get_tickets(
        self,
        existing_ids: list[int],
        limit: int,
        updated_since: str,
        ticket_type: str | None = None,
        workspace_id: str | None = None,
    ) -> list[Ticket]:
        """Get Tickets.

        Args:
            existing_ids (list[int]): List of existing IDs to filter.
            limit (int): Max number of tickets to return.
            updated_since (str): Date from which to fetch updated tickets.
            Date Format example: 2015-01-19T02:00:00Z.
            ticket_type (str| None): Ticket type. Possible values:
            Incident, Service Request or Alert. Defaults to None.
            workspace_id (str | None): Id of the workspace. If nothing is provided,
            it will list tickets only from the primary workspace.

        Returns:
            list[Ticket]: List of Ticket data models.
        """
        params = {
            "updated_since": updated_since,
            "order_type": "asc",
            "include": "requester, stats",
        }
        if ticket_type:
            params["type"] = ticket_type
        if workspace_id:
            params["workspace_id"] = workspace_id

        tickets = sorted(
            self._paginate_results(
                method="GET",
                url=self._get_full_url("list-tickets"),
                parser_method="build_ticket_obj_list",
                existing_ids=existing_ids,
                ids_attribute_to_filter="id",
                err_msg="Failed to list tickets",
                params=params,
            ),
            key=lambda x: x.updated_at_unix,
        )
        return tickets[:limit] if limit else tickets

    def get_departments(self, limit: Optional[int] = None) -> List[Department]:
        """
        Get departments
        :param: limit: {int} Max number of departments to return. If not specified, all departments will be returned.
        :return: {[Department]} List of Department data models
        """
        return self._paginate_results(
            method="GET",
            url=self._get_full_url("list-departments"),
            parser_method="build_department_obj_list",
            limit=limit,
            err_msg="Failed to list departments",
        )

    def get_locations(self, limit: Optional[int] = None) -> List[Location]:
        """
        Get locations
        :param limit: {int} Max number of locations to return. If not specified, all locations will be returned.
        :return: {[Location]} List of Location data models
        """
        return self._paginate_results(
            method="GET",
            url=self._get_full_url("list-locations"),
            parser_method="build_location_obj_list",
            limit=limit,
            err_msg="Failed to list locations",
        )

    def get_agent_groups(self, limit: Optional[int] = None) -> List[AgentGroup]:
        """
        Get agent groups
        :param: limit: {int} Max number of agent groups to return. If not specified, all agent groups will be returned.
        :return: {[AgentGroup]} List of Agent Group data models
        """
        return self._paginate_results(
            method="GET",
            url=self._get_full_url("list-agent-groups"),
            parser_method="build_agent_group_obj_list",
            limit=limit,
            err_msg="Failed to list agent groups",
        )

    def get_agents(self, limit: Optional[int] = None) -> List[Agent]:
        """
        Get agents
        :param: limit: {int} Max number agents to return. If not specified, all agents will be returned.
        :return: {[Agent]} List of Agent data models
        """
        return self._paginate_results(
            method="GET",
            url=self._get_full_url("list-agents"),
            parser_method="build_agent_obj_list",
            limit=limit,
            err_msg="Failed to list agents",
        )

    def create_ticket(
        self,
        type: Optional[str] = None,
        subject: Optional[str] = None,
        description: Optional[str] = None,
        requester_email: Optional[str] = None,
        responder_id: Optional[int] = None,
        group_id: Optional[int] = None,
        department_id: int | None = None,
        priority: Optional[int] = None,
        urgency: Optional[int] = None,
        impact: Optional[int] = None,
        status: Optional[int] = None,
        tags: Optional[List[str]] = None,
        custom_fields: Optional[Dict[str, str]] = None,
        attachments: Optional[List[str]] = None,
    ) -> Ticket:
        """Create Freshservice ticket.

        Args:
            type: Ticket's type. As of now, API v2 supports only type 'Incident'.
            subject: Subject of the ticket.
            description: HTML content of the ticket.
            requester_email: Email address of the requester.
            responder_id: ID of the agent to whom the ticket has been assigned.
            group_id: ID of the group to which the ticket has been assigned.
            department_id: ID of the department to which the ticket has been assigned.
            priority: Priority of the ticket. Numeric value - "Low": 1, "Medium": 2,
                "High": 3, "Urgent": 4.
            urgency: Urgency of the ticket. Numeric value - "Low": 1, "Medium": 2,
                "High": 3.
            impact: Impact of the ticket. Numeric value - "Low": 1, "Medium": 2,
                "High": 3.
            status: Status of the ticket. Numeric value - "Open" : 2, "Pending": 3,
                "Resolved": 4, "Closed": 5.
            tags: Tags for the ticket.
            custom_fields: Key value pairs containing the names and values of custom
                fields.
            attachments: List of file paths to attach to the ticket.

        Returns:
            Ticket: Created ticket data model.
        """
        payload = remove_none_dictionary_values(
            **{
                "type": type,
                "subject": subject,
                "description": description,
                "email": requester_email,
                "priority": priority,
                "status": status,
                "urgency": urgency,
                "impact": impact,
                "responder_id": responder_id,
                "group_id": group_id,
                "department_id": department_id,
                "custom_fields": custom_fields,
            }
        )
        url = self._get_full_url("create-ticket")
        if not attachments:
            if tags:
                payload["tags"] = tags
            response = self._session.post(url=url, json=payload)
        else:
            files = []
            for attachment in attachments:
                basename = os.path.basename(attachment)
                with open(attachment, "rb") as file:
                    file_content = file.read()
                    files.append(
                        (
                            "attachments[]",
                            (basename, file_content)
                        )
                    )

            del self._session.headers["Content-Type"]
            self._session.headers.update({"Accept": "application/json"})
            if tags:
                payload["tags[]"] = tags
            response = self._session.post(url=url, data=payload, files=files)

            del self._session.headers["Accept"]
            self._session.headers.update(deepcopy(HEADERS))

        self.validate_response(response, error_msg="Failed to create a ticket")
        return self._parser.build_created_ticket_obj(response.json())

    def update_ticket(
        self,
        ticket_id: Optional[int] = None,
        subject: Optional[str] = None,
        description: Optional[str] = None,
        requester_email: Optional[str] = None,
        responder_id: Optional[int] = None,
        group_id: Optional[int] = None,
        priority: Optional[int] = None,
        urgency: Optional[int] = None,
        impact: Optional[int] = None,
        status: Optional[int] = None,
        tags: Optional[List[str]] = None,
        custom_fields: Optional[Dict[str, str]] = None,
        attachments: Optional[List[str]] = None,
    ) -> Ticket:
        """
        Update Freshservice ticket
        :param ticket_id: {int} Ticket ID.
        :param subject: {str} Subject of the ticket.
        :param description: {str} HTML content of the ticket.
        :param requester_email: {str} Email address of the requester.
        :param responder_id: {int} ID of the agent to whom the ticket has been assigned
        :param group_id: {int} ID of the group to which the ticket has been assigned.
        :param priority: {int} Priority of the ticket. Numeric value - "Low": 1, "Medium": 2, "High": 3, "Urgent": 4
        :param urgency: {int} Urgency of the ticket. Numeric value - "Low": 1, "Medium": 2, "High": 3
        :param impact: {int} Impact of the ticket. Numeric value - "Low": 1, "Medium": 2, "High": 3
        :param status: {int} Status of the ticket. Numeric value - "Open" : 2, "Pending": 3, "Resolved": 4, "Closed": 5
        :param tags: {[str]} Tags for the ticket.
        :param custom_fields: {dict} Key value pairs containing the names and values of custom fields. Read more here: https://support.freshservice.com/support/solutions/articles/154126-customizing-ticket-fields
        :return: {Ticket} Updated ticket data model
        """
        payload = remove_none_dictionary_values(
            **{
                "subject": subject,
                "description": description,
                "email": requester_email,
                "priority": priority,
                "status": status,
                "urgency": urgency,
                "impact": impact,
                "responder_id": responder_id,
                "group_id": group_id,
                "custom_fields": custom_fields,
            }
        )
        url = self._get_full_url("update-ticket", ticket_id=ticket_id)
        if not attachments:
            if tags:
                payload["tags"] = tags
            response = self._session.put(url=url, json=payload)
        else:
            files = []
            for attachment in attachments:
                basename = os.path.basename(attachment)
                with open(attachment, "rb") as file:
                    file_content = file.read()
                    files.append(
                        (
                            "attachments[]",
                            (basename, file_content)
                        )
                    )

            del self._session.headers["Content-Type"]
            self._session.headers.update({"Accept": "application/json"})
            if tags:
                payload["tags[]"] = tags
            response = self._session.put(url=url, data=payload, files=files)

            del self._session.headers["Accept"]
            self._session.headers.update(deepcopy(HEADERS))

        self.validate_response(response, error_msg="Failed to update a ticket")
        return self._parser.build_updated_ticket_obj(response.json())

    def get_ticket(self, ticket_id: int) -> Ticket:
        """
        Get Freshservice ticket
        :param ticket_id: {int} Ticket ID
        :return: {Ticket} Ticket data model
        """
        response = self._session.get(
            self._get_full_url("get-ticket", ticket_id=ticket_id)
        )
        self.validate_response(response, error_msg=f"Failed to get ticket {ticket_id}")
        return self._parser.build_get_ticket_obj(response.json())

    def search_agent_by_attribute(self, attribute: str, attribute_value: str):
        """
        Search and match a single agent by an attribute
        :param attribute: {str} Agent's attribute to search for
        :param attribute_value: {str} Agent's attribute value to match
        :return: {Agent} Agent data model
        """
        try:
            self._siemplify_logger.info("Searching agents..")
            agents = self.get_agents()
        except Exception as error:
            self._siemplify_logger.error("Failed to list agents")
            self._siemplify_logger.exception(error)
            agents = []

        agent = [
            agent for agent in agents if getattr(agent, attribute) == attribute_value
        ]
        return agent[0] if agent else None

    def search_agent_group_by_attribute(self, attribute: str, attribute_value: str):
        """
        Search and match a single agent group by an attribute
        :param attribute: {str} Agent Group's attribute to search for
        :param attribute_value: {str} Agent Group's attribute value to match
        :return: {AgentGroup} Agent Group data model
        """
        try:
            self._siemplify_logger.info("Searching agent groups..")
            agent_groups = self.get_agent_groups()
        except Exception as error:
            self._siemplify_logger.error("Failed to list agent groups")
            self._siemplify_logger.exception(error)
            agent_groups = []

        group = [
            group
            for group in agent_groups
            if getattr(group, attribute) == attribute_value
        ]
        return group[0] if group else None

    def get_filtered_tickets(
        self,
        updated_since: str | None = None,
        limit: int | None = None,
        ticket_type: str | None = None,
        rows_per_page: int | None = None,
        start_at_page: int | None = None,
        include_requester: bool = True,
        requester_email: str | None = None,
        include_stats: bool = False,
        workspace_id: str | None = None,
    ) -> list[Ticket]:
        """Get  Filtered Tickets.

        Args:
            updated_since (str | None): Date from which to fetch updated tickets.
            Date Format example: 2015-01-19T02:00:00Z.
            limit (int | None): Max number of tickets to return.
            ticket_type (str | None): Ticket type. Possible values: Incident, Service
            Request or Alert.
            requester_email (str | None): Requester email of the ticket.
            rows_per_page (int | None): Page size of the pagination.
            start_at_page (int | None): Start page of the pagination.
            include_requester (bool): True if to include additional requester data of
            the ticket in the response, otherwise False.
            include_stats (bool): True if to include additional stats of the ticket in
            the response, otherwise False.
            workspace_id (str | None): Id of the workspace. If nothing is provided, it
            will get the tickets only from the primary workspace.

        Returns:
            list[Ticket]: List of Ticket data models.
        """
        params = {}
        if include_requester:
            params["include"] = "requester"
        if updated_since:
            params["updated_since"] = updated_since
        if include_stats:
            if include_requester:
                params["include"] = ",".join(["requester", "stats"])
            else:
                params["include"] = "stats"
        if ticket_type:
            params["type"] = ticket_type
        if requester_email:
            params["email"] = requester_email
        if workspace_id:
            params["workspace_id"] = workspace_id

        return self._paginate_results(
            **remove_none_dictionary_values(
                method="GET",
                url=self._get_full_url("list-tickets"),
                parser_method="build_ticket_obj_list",
                limit=limit,
                err_msg="Failed to list tickets",
                page_size=rows_per_page,
                start_page=start_at_page,
                params=params,
            )
        )

    def get_filtered_agents(
        self,
        agent_email: str = None,
        agent_state: str = None,
        include_not_active_agents: bool = None,
        rows_per_page: int = 30,
        start_at_page: int = 1,
        max_rows_to_return: int = 30,
    ) -> List[Agent]:
        """
        List Freshservice agents based on the specified search criteria.
        :param agent_email: {str} Email address to return agent records for.
        :param agent_state: {str} Agent states to return.
        :param include_not_active_agents: {bool} If enabled, results will include not active agent records.
        :param rows_per_page: {int} How many agent records should be returned per page for Freshservice pagination.
        :param start_at_page: {int} From which page agent records should be returned with Freshservice pagination.
        :param max_rows_to_return: {int} How many agent records action should return in total.
        :return: {[Agent]} List of Agent data models
        """
        params = {}
        if agent_email:
            params["email"] = agent_email
        if agent_state and agent_state != AGENT_STATE_ALL:
            params["state"] = agent_state
        if not include_not_active_agents:
            params["active"] = "true"

        return self._paginate_results(
            method="GET",
            url=self._get_full_url("list-agents"),
            parser_method="build_agent_obj_list",
            limit=max_rows_to_return,
            page_size=rows_per_page,
            start_page=start_at_page,
            err_msg="Failed to list agents",
            params=params,
        )

    def get_agent_roles(self, limit: Optional[int] = None) -> List[Role]:
        """
        Get agent roles
        :param: limit: {int} Max number of agent roles to return. If not specified, all agent roles will be returned.
        :return: {[Role]} List of Agent Roles data models
        """
        return self._paginate_results(
            method="GET",
            url=self._get_full_url("list-agent-roles"),
            parser_method="build_agent_roles_obj_list",
            limit=limit,
            err_msg="Failed to list agent roles",
        )

    def get_ticket_conversations(
        self,
        ticket_id: Optional[int] = None,
        limit: Optional[int] = None,
        rows_per_page: Optional[int] = None,
        start_at_page: Optional[int] = None,
    ) -> List[TicketConversation]:
        """
        Get Ticket conversations
        :param limit: {int} Max number of tickets to return
        :param ticket_id: {int} Ticket ID
        :param rows_per_page: {int} Page size of the pagination
        :param start_at_page: {int} Start page of the pagination
        :return: {[TicketConversation]} List of TicketConversation data models
        """
        return self._paginate_results(
            **remove_none_dictionary_values(
                method="GET",
                url=self._get_full_url(
                    "list-ticket-conversations", ticket_id=ticket_id
                ),
                parser_method="build_ticket_conversations_obj_list",
                limit=limit,
                err_msg=f"Failed to list ticket {ticket_id} conversations",
                page_size=rows_per_page,
                start_page=start_at_page,
            )
        )

    def get_requesters(self, limit: Optional[int] = None) -> List[Requester]:
        """
        Get Freshservice Requesters
        :param limit: {int} Max number of requesters to return
        :return: {[Requester]} List of Requester data models
        """
        return self._paginate_results(
            method="GET",
            url=self._get_full_url("list-requesters"),
            parser_method="build_requester_obj_list",
            limit=limit,
            err_msg="Failed to list requesters",
        )

    def get_filtered_requesters(
        self,
        requester_email: str = None,
        rows_per_page: int = 30,
        start_at_page: int = 1,
        max_rows_to_return: int = 30,
    ) -> List[Requester]:
        """
        List Freshservice requesters based on the specified search criteria.
        :param requester_email: {str} Email address to return requester records for.
        :param rows_per_page: {int} How many requester records should be returned per page for Freshservice pagination.
        :param start_at_page: {int} From which page requester records should be returned with Freshservice pagination.
        :param max_rows_to_return: {int} How many requester records action should return in total.
        :return: {[Requester]} List of Requester data models
        """
        params = {}
        if requester_email:
            params["email"] = requester_email

        return self._paginate_results(
            method="GET",
            url=self._get_full_url("list-requesters"),
            parser_method="build_requester_obj_list",
            limit=max_rows_to_return,
            page_size=rows_per_page,
            start_page=start_at_page,
            err_msg="Failed to list requesters",
            params=params,
        )

    def add_ticket_reply(self, ticket_id: str, reply_text: str) -> TicketConversation:
        """
        Add a Ticket Reply
        :param ticket_id: {int} Ticket ID
        :param reply_text: {str} Reply' text
        :return: {TicketConversation} TicketConversation data model
        """
        response = self._session.post(
            url=self._get_full_url("add-ticket-reply", ticket_id=ticket_id),
            json={"body": reply_text},
        )
        self.validate_response(
            response, error_msg=f"Failed to add a reply for ticket {ticket_id}"
        )
        return self._parser.build_ticket_reply_conversation_obj(response.json())

    def add_ticket_note(
        self, ticket_id: str, is_private: bool, note_text: str
    ) -> TicketConversation:
        """
        Add a Ticket Note
        :param ticket_id: {int} Ticket ID
        :param is_private: {bool} True if note should be private, False if note should be public
        :param note_text: {str} Note's text
        :return: {TicketConversation} TicketConversation data model
        """
        response = self._session.post(
            url=self._get_full_url("add-ticket-note", ticket_id=ticket_id),
            json={"body": note_text, "private": is_private},
        )
        self.validate_response(
            response,
            error_msg=(
                f"Failed to add {'private' if is_private else 'public'}"
                f" note for ticket {ticket_id}"
            ),
        )
        return self._parser.build_ticket_note_conversation_obj(response.json())

    def create_agent(
        self,
        email: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        is_occasional: Optional[bool] = None,
        can_see_all_tickets_from_associated_departments: Optional[bool] = None,
        department_ids: Optional[List[int]] = None,
        location_id: Optional[str] = None,
        member_of: Optional[List[int]] = None,
        roles: Optional[List[Dict]] = None,
        job_title: Optional[str] = None,
        custom_fields: Optional[List[Dict]] = None,
    ) -> Agent:
        """
        This operation allows you to create a new agent in Freshservice.
        :param email: {str} Email address of the agent.
        :param first_name: {str} First name of the agent.
        :param last_name: {str} Last name of the agent.
        :param is_occasional: {bool} True if the agent is an occasional agent, and false if full-time agent.
        :param can_see_all_tickets_from_associated_departments: {bool} 	Set to true if the agent must be allowed to view
            tickets filed by other members of the department, and false otherwise
        :param department_ids: {[int]} Unique IDs of the departments associated with the agent.
        :param location_id: {int} Unique ID of the location associated with the agent.
        :param member_of: {[int]} Unique IDs of the groups that the agent is a member of.
        :param roles: {[str]} Each individual role is a hash in the roles array that contains the attributes.
            role_id: Unique ID of the role assigned
            assignment_scope: The scope in which the agent can use the permissions granted by this role.
            Possible values include entire_helpdesk (all plans), member_groups
            (all plans; in the Forest plan, this also includes groups that the agent is an observer of),
            specified_groups (Forest only), and assigned_items (all plans)
            groups: Unique IDs of Groups in which the
            permissions granted by the role applies. Mandatory only when the assignment_scope is specified_groups, and
            should be ignored otherwise.
        :param job_title: {str} Job title of the agent.
        :param custom_fields: {Dict} Key-value pair containing the names and values of the (custom) agent fields.
        :return: {datamodels.Agent}
        """
        response = self._session.post(
            url=self._get_full_url("create-agent"),
            json=remove_none_dictionary_values(
                **{
                    "email": email,
                    "first_name": first_name,
                    "last_name": last_name,
                    "occasional": is_occasional,
                    "can_see_all_tickets_from_associated_departments": 
                    can_see_all_tickets_from_associated_departments,
                    "department_ids": department_ids,
                    "location_id": location_id,
                    "member_of": member_of,
                    "roles": roles,
                    "job_title": job_title,
                    "custom_fields": custom_fields,
                }
            ),
        )
        self.validate_response(response, error_msg="Failed to create an agent")
        return self._parser.build_agent_obj(response.json())

    def update_agent(
        self,
        agent_id: int,
        email: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        is_occasional: Optional[bool] = None,
        can_see_all_tickets_from_associated_departments: Optional[bool] = None,
        department_ids: Optional[List[int]] = None,
        location_id: Optional[str] = None,
        member_of: Optional[List[int]] = None,
        roles: Optional[List[Dict]] = None,
        job_title: Optional[str] = None,
        custom_fields: Optional[List[Dict]] = None,
    ) -> Agent:
        """
        This operation allows you to modify the profile of a particular agent.
        :param agent_id: {int} The ID of the agent to update.
        :param email: {str} Email address of the agent.
        :param first_name: {str} First name of the agent.
        :param last_name: {str} Last name of the agent.
        :param is_occasional: {bool} True if the agent is an occasional agent, and false if full-time agent.
        :param can_see_all_tickets_from_associated_departments: {bool} 	Set to true if the agent must be allowed to view
            tickets filed by other members of the department, and false otherwise
        :param department_ids: {[int]} Unique IDs of the departments associated with the agent.
        :param location_id: {int} Unique ID of the location associated with the agent.
        :param member_of: {[int]} Unique IDs of the groups that the agent is a member of.
        :param roles: {[str]} Each individual role is a hash in the roles array that contains the attributes.
            role_id: Unique ID of the role assigned
            assignment_scope: The scope in which the agent can use the permissions granted by this role.
            Possible values include entire_helpdesk (all plans), member_groups
            (all plans; in the Forest plan, this also includes groups that the agent is an observer of),
            specified_groups (Forest only), and assigned_items (all plans)
            groups: Unique IDs of Groups in which the
            permissions granted by the role applies. Mandatory only when the assignment_scope is specified_groups, and
            should be ignored otherwise.
        :param job_title: {str} Job title of the agent.
        :param custom_fields: {[Dict]} Key-value pair containing the names and values of the (custom) agent fields.
        :return: {datamodels.Agent} Agent data model.
        """
        response = self._session.put(
            url=self._get_full_url("update-agent", agent_id=agent_id),
            json=remove_none_dictionary_values(
                **{
                    "email": email,
                    "first_name": first_name,
                    "last_name": last_name,
                    "occasional": is_occasional,
                    "can_see_all_tickets_from_associated_departments": 
                    can_see_all_tickets_from_associated_departments,
                    "department_ids": department_ids,
                    "location_id": location_id,
                    "member_of": member_of,
                    "roles": roles,
                    "job_title": job_title,
                    "custom_fields": custom_fields,
                }
            ),
        )
        self.validate_response(response, error_msg="Failed to update an agent")
        return self._parser.build_agent_obj(response.json())

    def deactivate_agent(self, agent_id: str):
        """
        This operation allows you to deactivate a particular agent.
        :param agent_id: {str} The ID of the agent to deactivate.
        :return: {datamodels.Agent} Agent data model.
        """
        response = self._session.delete(
            url=self._get_full_url("deactivate-agent", agent_id=agent_id)
        )
        self.validate_response(
            response,
            error_msg="Failed to deactivate an agent",
            parse_response_error_message=False,
        )
        return self._parser.build_agent_obj(response.json())

    def create_requester(
        self,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        primary_email: Optional[str] = None,
        job_title: Optional[str] = None,
        location_id: Optional[int] = None,
        custom_fields: Optional[Dict[str, str]] = None,
        department_ids: Optional[List[int]] = None,
        can_see_all_tickets_from_associated_departments: Optional[bool] = None,
    ) -> Requester:
        """
        Create Freshservice requester
        :param first_name: {str} First name of the requester
        :param last_name: {str} Last name of the requester
        :param job_title: {str} Job title of the requester
        :param primary_email: {str} Primary email address of the requester
        :param can_see_all_tickets_from_associated_departments: {bool} Set to true if the requester must be allowed to view tickets filed by other members of the department, and false otherwise
        :param location_id: {int} Unique ID of the location associated with the requester.
        :param department_ids: {[int]} Unique IDs of the departments associated with the requester.
        :param custom_fields: {dict} Key value pairs containing the names and values of custom fields. Read more here: https://support.freshservice.com/support/solutions/articles/154126-customizing-ticket-fields
        :return: {Requester} Created Requester data model
        """
        response = self._session.post(
            url=self._get_full_url("create-requester"),
            json=remove_none_dictionary_values(
                **{
                    "primary_email": primary_email,
                    "job_title": job_title,
                    "first_name": first_name,
                    "last_name": last_name,
                    "department_ids": department_ids,
                    "can_see_all_tickets_from_associated_departments": 
                    can_see_all_tickets_from_associated_departments,
                    "location_id": location_id,
                    "custom_fields": custom_fields,
                }
            ),
        )
        self.validate_response(response, error_msg="Failed to create a requester")
        return self._parser.build_created_requester_obj(response.json())

    def update_requester(
        self,
        requester_id: int,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        primary_email: Optional[str] = None,
        job_title: Optional[str] = None,
        location_id: Optional[int] = None,
        custom_fields: Optional[Dict[str, str]] = None,
        department_ids: Optional[List[int]] = None,
        can_see_all_tickets_from_associated_departments: Optional[bool] = None,
    ) -> Requester:
        """
        Update Freshservice requester
        :param requester_id: {int} Requester ID
        :param first_name: {str} First name of the requester
        :param last_name: {str} Last name of the requester
        :param job_title: {str} Job title of the requester
        :param primary_email: {str} Primary email address of the requester
        :param can_see_all_tickets_from_associated_departments: {bool} Set to true if the requester must be allowed to view tickets filed by other members of the department, and false otherwise
        :param location_id: {int} Unique ID of the location associated with the requester.
        :param department_ids: {[int]} Unique IDs of the departments associated with the requester.
        :param custom_fields: {dict} Key value pairs containing the names and values of custom fields. Read more here: https://support.freshservice.com/support/solutions/articles/154126-customizing-ticket-fields
        :return: {Requester} Updated Requester data model
        """
        response = self._session.put(
            url=self._get_full_url("update-requester", requester_id=requester_id),
            json=remove_none_dictionary_values(
                **{
                    "primary_email": primary_email,
                    "job_title": job_title,
                    "first_name": first_name,
                    "last_name": last_name,
                    "department_ids": department_ids,
                    "can_see_all_tickets_from_associated_departments": 
                    can_see_all_tickets_from_associated_departments,
                    "location_id": location_id,
                    "custom_fields": custom_fields,
                }
            ),
        )
        self.validate_response(
            response, error_msg=f"Failed to update requester with id {requester_id}"
        )
        return self._parser.build_updated_requester_obj(response.json())

    def deactivate_requester(self, requester_id: str):
        """
        Deactivate requester
        :param requester_id: {str} ID of the requester to deactivate
        """
        response = self._session.delete(
            url=self._get_full_url("deactivate-requester", requester_id=requester_id)
        )
        self.validate_response(
            response, error_msg=f"Failed to deactivate requester with id {requester_id}"
        )

    def get_ticket_time_entries(
        self,
        ticket_id: Optional[int] = None,
        limit: Optional[int] = None,
        rows_per_page: Optional[int] = None,
        start_at_page: Optional[int] = None,
    ) -> List[TicketTimeEntry]:
        """
        List Ticket Time Entries
        :param limit: {int} Max number of tickets to return. If not specified, all ticket's time entries will be returned
        :param ticket_id: {int} Ticket ID
        :param rows_per_page: {int} Page size of the pagination
        :param start_at_page: {int} Start page of the pagination
        :return: {[TicketTimeEntry]} List of TicketTimeEntry data models
        """
        return self._paginate_results(
            method="GET",
            url=self._get_full_url("list-ticket-time-entries", ticket_id=ticket_id),
            parser_method="build_ticket_time_entry_obj_list",
            limit=limit,
            page_size=rows_per_page,
            start_page=start_at_page,
            err_msg=f"Failed to list time entries for ticket {ticket_id}",
        )

    def add_ticket_time_entry(
        self,
        ticket_id: str,
        agent_id: int = None,
        time_running: Optional[bool] = None,
        time_spent: Optional[str] = None,
        billable: Optional[bool] = None,
        note: Optional[str] = None,
        custom_fields: Optional[dict] = None,
    ) -> TicketTimeEntry:
        """
        Create Ticket Time Entry
        :param ticket_id: {str} The ID of the ticket to create time entry for
        :param agent_id: {int} The ID of the agent the time entry is tracked for
        :param time_running: {bool} True if timer should be running, otherwise False
        :param time_spent: {str} Time spent for the time entry, in format "HH:MM"
            Note -
                1) If timer_running is not specified in the request, it is considered as false and time_spent is mandatory in this scenario.
                2) time_spent can be set only if timer_running is false or not set.
        :param billable: {bool} True if time entry is billable, otherwise False
        :param note: {str} Time entry's note
        :param custom_fields: {dict} Key value pairs containing the names and values of custom fields. Read more here: https://support.freshservice.com/support/solutions/articles/50000003609-adding-custom-fields-for-time-entries
        :return: {TicketTimeEntry} Created TicketTimeEntry data model
        """
        response = self._session.post(
            url=self._get_full_url("add-ticket-time-entry", ticket_id=ticket_id),
            json=remove_none_dictionary_values(
                **{
                    "timer_running": time_running,
                    "time_spent": time_spent,
                    "agent_id": agent_id,
                    "billable": billable,
                    "note": note,
                    "custom_fields": custom_fields,
                }
            ),
        )
        self.validate_response(
            response, error_msg=f"Failed to add time entry for ticket {ticket_id}"
        )
        return self._parser.build_added_ticket_time_entry_obj(response.json())

    def update_ticket_time_entry(
        self,
        ticket_id: str,
        time_entry_id: int,
        agent_id: int = None,
        time_running: Optional[bool] = None,
        time_spent: Optional[str] = None,
        billable: Optional[bool] = None,
        note: Optional[str] = None,
        custom_fields: Optional[dict] = None,
    ) -> TicketTimeEntry:
        """
        Update Ticket Time Entry
        :param ticket_id: {str} The ID of the ticket to update time entry for
        :param time_entry_id: {int} ID of the Time Entry to update
        :param agent_id: {int} The ID of the agent the time entry is tracked for
        :param time_running: {bool} True if timer should be running, otherwise False
        :param time_spent: {str} Time spent for the time entry, in format "HH:MM"
            Note - For a running timer, time_spent cannot be updated without stopping it.
        :param billable: {bool} True if time entry is billable, otherwise False
        :param note: {str} Time entry's note to update
        :param custom_fields: {dict} Key value pairs containing the names and values of custom fields. Read more here: https://support.freshservice.com/support/solutions/articles/50000003609-adding-custom-fields-for-time-entries
        :return: {TicketTimeEntry} Update TicketTimeEntry data model
        """
        response = self._session.put(
            url=self._get_full_url(
                "update-ticket-time-entry",
                ticket_id=ticket_id,
                time_entry_id=time_entry_id,
            ),
            json=remove_none_dictionary_values(
                **{
                    "timer_running": time_running,
                    "time_spent": time_spent,
                    "agent_id": agent_id,
                    "billable": billable,
                    "note": note,
                    "custom_fields": custom_fields,
                }
            ),
        )
        self.validate_response(
            response,
            error_msg=(
                f"Failed to update time entry {time_entry_id} "
                f"for ticket {ticket_id}"
            ),
        )
        return self._parser.build_updated_ticket_time_entry_obj(response.json())

    def delete_ticket_time_entry(self, ticket_id: int, time_entry_id: int):
        """
        Delete Ticket Time Entry
        :param ticket_id: {int} The ID of the ticket to delete time entry for
        :param time_entry_id: {int} ID if the Time Entry to delete
        """
        response = self._session.delete(
            url=self._get_full_url(
                "delete-ticket-time-entry",
                ticket_id=ticket_id,
                time_entry_id=time_entry_id,
            )
        )
        self.validate_response(
            response,
            error_msg=(
                f"Failed to delete time entry {time_entry_id} "
                f"for ticket {ticket_id}"
            ),
        )
