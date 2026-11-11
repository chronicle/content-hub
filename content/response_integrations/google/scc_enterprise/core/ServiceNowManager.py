from __future__ import annotations

import json
import urllib.parse
from datetime import datetime
from typing import Iterable, Sequence, TypeVar
from urllib.parse import urljoin

import requests

from soar_sdk.SiemplifyUtils import pytz

from TIPCommon.base.utils import CreateSession, NewLineLogger
from TIPCommon.consts import NUM_OF_MILLI_IN_SEC
from TIPCommon.types import SingleJson
from scc_enterprise.core import SCCEnterpriseConsts
from scc_enterprise.core import ServiceNowConsts
from scc_enterprise.core import ServiceNowDatamodels
from scc_enterprise.core import ServiceNowTableFields
from scc_enterprise.core import ServiceNowParser as parser
from scc_enterprise.core.SCCEnterpriseExceptions import SCCEnterpriseManagerException
from scc_enterprise.core.ServiceNowExceptions import (
    SNowException,
    SNowNotFoundException,
    SNowPermissionDeniedException,
    SNowRecordNotFoundException,
    SNowTableNotFoundException,
)


SNowDataModel = TypeVar("SNowDataModel", bound=ServiceNowDatamodels.SNBaseEntry)

HEADERS = {"Accept": "application/json", "Content-Type": "application/json"}


class ServiceNowManager:

    def __init__(
        self,
        api_root: str,
        username: str,
        password: str,
        default_incident_table: str = (ServiceNowConsts.CUSTOM_TICKET_TABLE_NAME),
        verify_ssl: bool = False,
        siemplify_logger: NewLineLogger | None = None,
        client_id: str | None = None,
        client_secret: str | None = None,
        refresh_token: str | None = None,
        use_oauth: bool = False,
    ) -> None:
        """
        The method is used to init an object of ServiceNowManager class.

        Params:
            api_root: API root of the server.
            username: Username of the account.
            password: Password of the account.
            default_incident_table: Default incident table
            verify_ssl:
                Enable (True) or disable (False).
                If enabled, verify the SSL certificate for the connection.
            siemplify_logger: Siemplify logger.
            client_id:
                Client ID of ServiceNow application.
                Required for Oauth authentication.
            client_secret:
                Client Secret of ServiceNow application.
                Required for Oauth authentication.
            refresh_token:
                Refresh token for ServiceNow application.
                Required for Oauth authentication.
            use_oauth:
                If enabled, integration will use Oauth authentication.
                Parameters "Client ID", "Client Secret" and "Refresh Token"
                are mandatory.
        """
        self.api_root = api_root
        self.username = username
        self.password = password
        self.default_incident_table = default_incident_table
        self.siemplify_logger = siemplify_logger
        self.client_id = client_id
        self.client_secret = client_secret
        self.refresh_token = refresh_token
        self.use_oath = use_oauth
        self.session = CreateSession.create_session()
        self.session.verify = verify_ssl
        self.session.headers = HEADERS
        self.parser = parser
        self.removed_headers = {}

        if not self.use_oath:
            self.session.auth = (username, password)
            return

        if not all((self.client_id, self.client_secret, self.refresh_token)):
            raise SCCEnterpriseManagerException(
                "Please specify Client ID, Client Secret and Refresh Token "
                "for OAuth authentication."
            )
        self.session.headers.update(
            {
                "Authorization": f"Bearer {self.get_access_token()}",
                "Content-Type": "application/json",
            }
        )

    def get_access_token(self) -> str:
        """Get access token to use in requests.

        Returns:
            Access token.
        """
        request_url = self._get_full_url(
            "get_tokens", general_api=True, part_to_remove="api/now/v1/"
        )
        self.session.headers.update(
            {"Content-Type": "application/x-www-form-urlencoded"}
        )
        payload = {
            "grant_type": "refresh_token",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": self.refresh_token,
        }
        response = self.session.post(request_url, data=payload)
        self.validate_response(response)
        return response.json().get("access_token")

    def _get_full_url(
        self,
        url_id: str,
        general_api: bool = False,
        part_to_remove: str = "v1",
        **kwargs,
    ) -> str:
        """Get full url from url identifier.

        Params:
            url_id: The id of url
            general_api: whether to use general api or not
            part_to_remove: Part of url to remove, e.g. v1
            kwargs: Variables passed for string formatting

        Returns:
            Full formatted uri
        """
        api_root = (
            self.remove_version_from_api_root(self.api_root, part_to_remove)
            if general_api
            else self.api_root
        )
        return urljoin(
            api_root, ServiceNowConsts.SNOW_API_ENDPOINTS[url_id].format(**kwargs)
        )

    def get_system_timezone_by_user_name(self, user_name: str) -> str:
        """Get System timezone from a user_id (preferably caller_id/admin user)

        Args:
            user_name: A unique username to fetch timezone from

        Raises:
            SNowNotFoundException:
                In case timezone cannot be parsed by pytz

        Returns:
            str: The timezone as a string parsable by pytz
        """
        response = self.session.get(
            self._get_full_url("get_user_details"),
            params={
                "sysparm_query": f"user_name={user_name}",
                "sysparm_fields": "time_zone",
            },
        )
        self.validate_response(response=response)
        results: list[SingleJson] = response.json()["result"]
        if not results:
            raise SNowNotFoundException(
                f"didn't find any results for timezones by user '{user_name}'"
            )

        # Assuming the username is unique only one item should be here
        user_fields = results[0]
        if "time_zone" not in user_fields:
            raise ValueError(
                'The key "time_zone" is missing in the request\'s result\n'
                f"Timezone results: {user_fields}"
            )

        # Since we provide 1 user we expect 1 result, so we take result[0]
        timezone: str = user_fields["time_zone"]
        timezone = (
            timezone.replace(" ", "_") if timezone else ServiceNowConsts.DEFAULT_TZ
        )

        if timezone not in pytz.all_timezones_set:
            raise SNowNotFoundException(
                "The fetched system time zone is not listed in "
                "pytz.all_timezones. Please check if it was parsed correctly.\n"
                f'Received time zone: "{timezone}"'
            )

        return timezone

    def get_incidents_by_sys_ids(
        self,
        numbers: Sequence[str],
        table_name: str | None = None,
        fields: Iterable[str] = None,
        page_size: int = ServiceNowConsts.DEFAULT_PAGE_SIZE,
    ) -> list[ServiceNowDatamodels.Incident]:
        """Retrieve incidents by their sys_id

        Args:
            numbers: Sequence of ticket numbers to search for
            table_name: Specific table name. Defaults to incident
            fields: Specified record fields
            page_size: Limit incidents for pagination

        Returns:
            list[Incident]:
                A list of Incident objects for each incident returned
        """
        table_name = self.get_table_name(table_name)
        params = {"sysparm_display_value": "true", "sysparm_limit": page_size}
        incidents = []

        if fields:
            params["sysparm_fields"] = ",".join(fields)

        for index in range(0, len(numbers), page_size):
            keys_to_search = numbers[index : index + page_size]
            number_query = self.__get_param_query_fragment(
                key="sys_id", values=keys_to_search, join_char="^OR"
            )

            params["sysparm_query"] = self.__build_system_query([number_query])
            params["sysparm_suppress_pagination_header"] = True

            response = self.session.get(
                self._get_full_url("get_incidents", table=table_name), params=params
            )

            try:
                self.validate_response(response)
                results = self.parser.build_incidents(response.json())
                incidents.extend(results)
            except SNowRecordNotFoundException:
                self.siemplify_logger.info(
                    f"Number query for keys: {keys_to_search} did not return any "
                    f"results. Skipping ..."
                )

        return incidents

    def get_incidents_with_pagination(
        self,
        table_name: str | None = None,
        fields: Iterable[str] = None,
        page_size: int = ServiceNowConsts.DEFAULT_PAGE_SIZE,
        limit: int | None = None,
        updated_after: int | None = None,
    ) -> list[ServiceNowDatamodels.Incident]:
        """Find incidents with filters

        Args:
            table_name: Specific table name. Defaults to incident
            fields: Specified record fields
            page_size: Limit incidents for pagination
            limit: Limit of incidents to fetch in total
            updated_after: Fetch incident updated on or after this time (unix)

        Returns:
            list[Incident]:
                A list of Incident objects for each incident returned
        """
        table_name = self.get_table_name(table_name)
        params = {"sysparm_display_value": "true"}
        sysparm_queries = []

        if updated_after is not None:
            updated_after_datetime = datetime.fromtimestamp(
                updated_after // NUM_OF_MILLI_IN_SEC
            ).strftime(ServiceNowConsts.DATETIME_FORMAT)

            after_time_filter = f"sys_updated_on>={updated_after_datetime}"
            sysparm_queries.append(after_time_filter)

        if fields:
            params["sysparm_fields"] = ",".join(fields)

        params["sysparm_query"] = self.__build_system_query(sysparm_queries)
        return self._fetch_incidents(table_name, params, page_size, limit)

    def _fetch_incidents(
        self,
        table_name: str,
        params: dict[str, str | int | bool],
        page_size: int = ServiceNowConsts.DEFAULT_PAGE_SIZE,
        limit: int | None = None,
    ) -> list[ServiceNowDatamodels.Incident]:
        """Fetch incidents from ServiceNow in chunks of page_size.

        Args:
            table_name: Specific table name. Defaults to incident
            params: Parameters to filter incidents with
            page_size: Limit incidents for pagination
            limit: Limit of incidents to fetch in total

        Returns:
            list[Incident]: A list of Incident objects for each incident
        """
        params["sysparm_limit"] = page_size
        params["sysparm_suppress_pagination_header"] = True
        start_offset = 0
        incidents = []

        while limit is None or len(incidents) < limit:
            params["sysparm_offset"] = start_offset
            response = self.session.get(
                self._get_full_url("get_incidents", table=table_name), params=params
            )

            try:
                self.validate_response(response)
                results = self.parser.build_incidents(response.json())
            except SNowRecordNotFoundException:
                results = []

            if not results:
                break

            incidents.extend(results)
            start_offset += len(results)

            if len(results) < page_size:
                break

        return incidents[:limit] if limit is not None else incidents

    def get_ticket_comments(
        self,
        ticket_sys_ids: Iterable[str],
        page_size: int = ServiceNowConsts.DEFAULT_PAGE_SIZE,
        fields: list | None = None,
        table_name: str | None = None,
        order_by: str | None = None,
    ) -> list[ServiceNowDatamodels.Comment]:
        """
        Retrieve ticket comments with limit
        :param ticket_sys_ids: {Iterable[str]} ticket sys_id
        :param page_size: {int} comments per page
        :param fields: {list} specified record fields
        :param table_name: {str} specified table name (incident)
        :param order_by: {str} specified table name (incident)
        :return: {list} Incident comments {Comment}
        """
        params = {}
        sysparm_queries = []
        param_keys = ["u_additional_comments"]

        sys_param_query = self.__get_param_query_fragment(
            "element", param_keys, join_char="^OR"
        )
        sysparm_queries.append(sys_param_query)

        sys_param_query = self.__get_param_query_fragment(
            "element_id", ticket_sys_ids, join_char="^OR"
        )
        sysparm_queries.append(sys_param_query)

        if fields:
            params["sysparm_fields"] = ",".join(fields)

        if order_by:
            sysparm_queries.append(f"ORDERBY{order_by}")

        params["sysparm_query"] = self.__build_system_query(sysparm_queries)
        params["sysparm_limit"] = page_size
        params["sysparm_suppress_pagination_header"] = True

        comments = []

        while True:
            params["sysparm_offset"] = len(comments)
            response = self.session.get(
                self._get_full_url("get_comments", table=table_name), params=params
            )
            self.validate_response(response)
            results = self.parser.build_results(response.json(), "build_comment")

            comments.extend(results)

            if len(results) < page_size:
                break

        return comments

    def get_ticket_id(self, ticket_number: str, table_name: str | None = None) -> str:
        """
        Find sys_id base on number
        :param ticket_number: {str} ticket number
        :param table_name: {str} specified table name (incident)
        :return: ticket_id {str}
        """
        table_name = table_name if table_name else self.default_incident_table
        search_params = f"number={ticket_number}"
        response = self.session.get(
            self._get_full_url("get_incidents", table=table_name),
            params={"sysparm_query": search_params},
        )
        self.validate_response(response)
        incidents = self.parser.build_results(response.json(), "build_incident")
        if incidents:
            return incidents[0].sys_id

    def get_table_name(self, table_name: str | None = None) -> str:
        """
        Get table name
        :param table_name: {str}
        :return: {str} Table name
        """
        return table_name if table_name else self.default_incident_table

    def get_group_id(self, group_name: str) -> str | None:
        """
        Find group_sys_id base on group_name
        :param group_name: {str} full group name
        :return: {str} group_id
        """
        search_params = f"name={group_name}"
        response = self.session.get(
            self._get_full_url("get_group_id"), params={"sysparm_query": search_params}
        )
        try:
            self.validate_response(response)
            groups = self.parser.build_results(response.json(), "build_object")
            if groups:
                return groups[0].sys_id

        except Exception:
            raise SNowNotFoundException(f"Group with name {group_name} not found")

    def get_user_id(
        self, user_name: str, property_string: str = "name={}"
    ) -> str | None:
        """
        Find user_sys_id base on user_name
        :param user_name: {str} user full name
        :param property_string: {str} search param string
        :return: {str} user_id
        """
        search_params = property_string.format(user_name)
        response = self.session.get(
            self._get_full_url("get_user_details"),
            params={"sysparm_query": search_params},
        )
        try:
            self.validate_response(response)
            users = self.parser.build_results(response.json(), "build_object")
            if users:
                return users[0].sys_id

        except Exception:
            raise SNowNotFoundException(f"User with name {user_name} not found")

    def update_incident(
        self,
        ticket_number: str,
        table_name: str | None = None,
        short_description: str | None = None,
        impact: int | None = None,
        urgency: int | None = None,
        category: str | None = None,
        assignment_group: str | None = None,
        assigned_to: str | None = None,
        comments: str | None = None,
        description: str | None = None,
        incident_state: str | int | None = None,
        close_notes: str | None = None,
        close_code: str | None = None,
        custom_fields: dict | None = None,
        work_notes: str | None = None,
        is_ticket_id: bool = False,
    ) -> tuple[ServiceNowDatamodels.Ticket, list[str]]:
        """
        Inserts one record in the specified table.
        :param ticket_number: {str}
        :param table_name: {str}
        :param short_description: {str}
        :param impact: {int} 1-High, 2-Medium, 3-Low
        :param urgency: {int} 1-High, 2-Medium, 3-Low
        :param category: {str} (Help, Database, Network, software, hardware)
        :param assignment_group: {str} assignment_group full name
        :param assigned_to: {str} assigned user full name (first last)
        :param comments: {str}
        :param description: {str}
        :param incident_state: {str | int | None} status name or status id
        :param close_notes: {str} notes for closing incident
        :param close_code: {str} incident resolution code
        :param custom_fields: {dict} custom fields
        :param work_notes: {str}
        :param is_ticket_id: Whether the provided ticket number is a sys ID
        :return: {Ticket, list} Updated ticket, list of not updated fields
        """
        # Check which fields the user want to update.
        table_name = self.get_table_name(table_name)
        update_payload = {}
        if short_description:
            update_payload["short_description"] = short_description

        if impact:
            update_payload["impact"] = impact

        if urgency:
            update_payload["urgency"] = urgency

        if category:
            update_payload["category"] = category

        if assignment_group:
            assignment_group_id = self.get_group_id(assignment_group)
            update_payload["assignment_group"] = assignment_group_id

        if assigned_to:
            assign_user_id = self.get_user_id(assigned_to)
            update_payload["assigned_to"] = assign_user_id

        if comments:
            update_payload["comments"] = comments

        if description:
            update_payload["description"] = description

        if incident_state:
            update_payload["state"] = incident_state

        if close_notes:
            update_payload["close_notes"] = close_notes

        if close_code:
            update_payload["close_code"] = close_code

        if work_notes:
            update_payload["work_notes"] = work_notes

        if custom_fields:
            update_payload.update(custom_fields)

        # Get ticket sys_id base on ticket number
        ticket_id = ticket_number
        if not is_ticket_id:
            ticket_id = self.get_ticket_id(ticket_number, table_name)

        url = self._get_full_url("update_incident", table=table_name, ticket=ticket_id)
        response = self.session.put(url, json=update_payload)
        self.validate_response(response)
        ticket = self.parser.build_result(response.json(), "build_ticket")
        updated_ticket_json = ticket.to_json()
        not_used_custom_keys = []
        # Check if data successfully updated
        # API returns status_code 200 even if the field not successfully updated
        for key in update_payload:
            # TODO: Check if u_overview can be specifically tested with special
            #       html escaping and json dumping
            excluded_fields = {
                "comments",
                "state",
                "work_notes",
                "u_additional_comments",
                "u_overview",
            }
            if key in excluded_fields:
                continue

            excluded_dict_fields = {"assigned_to", "u_assigned_to", "assignment_group"}
            if key in excluded_dict_fields:
                if update_payload[key] != updated_ticket_json[key]["value"]:
                    raise SNowException(
                        f"Could not update {key} with value: "
                        f"{update_payload[key]!r}."
                    )

                continue

            if (
                key in updated_ticket_json
                and update_payload[key] != updated_ticket_json[key]
            ):
                raise SNowException(
                    f"Could not update {key} with value: "
                    f"{updated_ticket_json[key]!r}."
                )

            if key not in updated_ticket_json and key in custom_fields:
                not_used_custom_keys.append(key)

        return ticket, not_used_custom_keys

    def close_incident(
        self,
        ticket_number: str,
        close_reason: str,
        close_notes: str | None = None,
        close_code: str | None = None,
        is_ticket_id: bool = False,
    ) -> ServiceNowDatamodels.Ticket:
        """
        Retrieve incident sys_id and change state to close
        Note: state are different from table object to another
        :param ticket_number: {str}
        :param close_reason: {str}
        :param close_notes: {str} notes for closing incident
        :param close_code: {str} incident resolution code
        :param is_ticket_id: Whether the provided ticket number
            is a ticket sys ID
        :return: {ServiceNowDatamodels.Ticket} incident_id if updated, else none
        """
        params = {"u_status": SCCEnterpriseConsts.RESOLVED_STATUS}
        if close_reason:
            params.update({"u_additional_comments": close_reason})

        incident_number, _ = self.update_incident(
            ticket_number,
            custom_fields=params,
            close_notes=close_notes,
            close_code=close_code,
            is_ticket_id=is_ticket_id,
        )
        return incident_number

    def add_comment_to_incident(
        self,
        ticket_number: str,
        comment: str,
        table_name: str | None = None,
        is_ticket_id: bool = False,
    ) -> ServiceNowDatamodels.Ticket:
        """
        Retrieve incident sys_id and add comment to incident
        :param ticket_number: {str}
        :param comment: {str}
        :param table_name: {str}
        :param is_ticket_id: Whether the ticket number is a ticket sys ID
        :return: {ServiceNowDatamodels.Ticket} incident_id if updated, else none
        """
        incident_number, _ = self.update_incident(
            ticket_number,
            custom_fields={"u_additional_comments": comment},
            table_name=self.get_table_name(table_name),
            is_ticket_id=is_ticket_id,
        )
        return incident_number

    @staticmethod
    def remove_version_from_api_root(api_root: str, version_to_remove: str) -> str:
        """
        Removes the version from the given root api.

        Params:
            api_root: Full Api Root given by the user
            version_to_remove: Version to remove, e.g. v1

        Returns:
            Api Root without the version
        """
        api_root = (
            urllib.parse.urlparse(api_root)
            .geturl()
            .replace(f"/{version_to_remove}", "")
        )
        return api_root

    @classmethod
    def check_and_raise_not_found_exceptions(
        cls, exception: requests.HTTPError
    ) -> None:
        """
        Raise exception if exception is not found exception.

        Params:
            exception: The api error

        Raises:
            SNowTableNotFoundException if applicable
        """
        error_message = (
            cls.get_api_error_message(exception) or exception.response.content.decode()
        )

        if "Invalid table" in error_message:
            raise SNowTableNotFoundException(error_message)

        status_code = exception.response.status_code
        if status_code == ServiceNowConsts.NOT_FOUND_STATUS:
            raise SNowRecordNotFoundException(error_message)

        if status_code == ServiceNowConsts.CLASS_NOT_FOUND_STATUS:
            raise SNowNotFoundException(error_message)

    @staticmethod
    def get_api_error_message(exception: requests.HTTPError) -> str | None:
        """
        Get API error message.

        Params:
            exception: The api error

        Returns:
            error message | None
        """
        try:
            response_json = json.loads(exception.response.content)
            return response_json.get("error", {}).get("message")

        except Exception:
            return

    @classmethod
    def validate_response(
        cls,
        response: requests.Response,
        error_msg: str = "An error occurred",
        force_json_result: bool = True,
    ) -> None:
        """
        Validate response.

        Params:
            response: The response to validate
            error_msg: Default message to display on error
            force_json_result: If True raise exception if result is not json

        Returns:
            True if validation successful

        Raises:
            SNowPermissionDeniedException, JsonDecodeError, Exception
        """
        try:
            response.raise_for_status()
            if force_json_result:
                response.json()

        except requests.HTTPError as error:
            cls.check_and_raise_not_found_exceptions(error)
            clean_error_message = cls.get_api_error_message(error)

            if clean_error_message:
                if response.status_code == 403:
                    raise SNowPermissionDeniedException(clean_error_message)

                raise Exception(clean_error_message)

            raise Exception(f"{error_msg}: {error} {error.response.content}")

    def create_or_update_entry(
        self, entry: SNowDataModel, create_if_not_found: bool = True
    ) -> SNowDataModel:
        """
        Create entry from provided entry data model, or update an existing one.

        Params:
            entry:
                SNBaseEntry data model.
                Should have table_name set to a proper value
            create_if_not_found: Do we want to create entity if it wasn't found

        Returns:
            SNBaseEntry
        """
        table_uri = self._get_full_url("tables", table=entry.table_name)

        try:
            response = self.session.get(table_uri, params=entry.to_search_params())

            self.validate_response(response)
            if not response.json()["result"]:
                raise SNowNotFoundException(
                    "Entry was not found with provided search params"
                )

            entry_json = response.json()["result"][0]

            response = self.session.patch(
                f"{table_uri}/{entry_json['sys_id']}", json=entry.to_json()
            )
            self.validate_response(response)
            return self.parser.parse_sn_entry(
                entry.__class__, response.json()["result"]
            )

        except SNowNotFoundException:
            if create_if_not_found is False:
                raise

        response = self.session.post(table_uri, json=entry.to_json())
        self.validate_response(response)
        return self.parser.parse_sn_entry(entry.__class__, response.json()["result"])

    def create_table(
        self,
        table: ServiceNowDatamodels.SNTable,
        table_fields: list[ServiceNowDatamodels.SNTableField],
    ) -> ServiceNowDatamodels.SNTable:
        """
        Create table with given table, user role and fields datamodels

        Params:
            table: data model representing a table entry
            user_role: data model representing a user role entry
            table_fields: List of fields to be added to the table

        Returns:
            SNTable data model parsed from create table request
        """
        # First step would be to create a table
        table = self.create_or_update_entry(table)

        # Now we can update table_fields with proper table name and
        # add them 1 by 1
        for table_field in table_fields:
            table_field.name = table.name
            _table_field = self.create_or_update_entry(table_field)

            # Populate choices if the field has predefined choices
            for choice_name in table_field.choices or []:
                choice = ServiceNowDatamodels.SNChoice(
                    element=_table_field.element,
                    name=_table_field.name,
                    value=choice_name,
                    label=choice_name,
                )
                self.create_or_update_entry(choice)

        # Create activity system property
        fields_csv = ",".join(
            t_field.element
            for t_field in table_fields
            if t_field.element != "u_overview"
        )
        system_property = ServiceNowDatamodels.SNSystemProperty(
            description=f"{table.label} activity formatter fields",
            name=f"glide.ui.{table.name}_activity.fields",
            value=(
                f"{fields_csv}"
                f"{ServiceNowTableFields.ACTIVITY_FORMATTER_FIELDS_EXTRA}"
            ),
        )
        self.create_or_update_entry(system_property)

        return table

    def create_application(
        self,
        application_menu: ServiceNowDatamodels.SNApplicationMenu,
        application_module: ServiceNowDatamodels.SNApplicationModule,
    ) -> ServiceNowDatamodels.SNApplicationModule:
        """
        Create application menu and application module.

        Params:
            table: data model representing a table entry
            application_menu: data model representing an app
            application_module: data model representing an app module

        Returns:
            SNApplicationModule data model parsed from create app module request
        """
        # First we need to create an application
        app_menu = self.create_or_update_entry(application_menu)

        # Now we can update app module data with proper application sys_id
        application_module.application = app_menu.sys_id
        app_module = self.create_or_update_entry(application_module)

        return app_module

    def create_form_ui_view(
        self,
        table: ServiceNowDatamodels.SNTable,
        ui_view: ServiceNowDatamodels.SNUiView,
        ui_sections: list[ServiceNowDatamodels.SNUiSection],
    ) -> ServiceNowDatamodels.SNUiView:
        """
        Create Form UI View with given table, UI view role and UI sections data
        models.

        Params:
            table: data model representing a table entry
            ui_view: data model representing a UI view
            ui_sections:
                List of sections to be added to the form view (with fields)

        Returns:
            SNUiView data model parsed from create view request
        """
        # First we need to create (or fetch) an ui view and ui_form linked to it
        _ui_view = self.create_or_update_entry(ui_view)
        ui_form = ServiceNowDatamodels.SNUiForm(name=table.name, view=_ui_view.sys_id)
        _ui_form = self.create_or_update_entry(ui_form)

        # Second step would be to create sections and link them to form sections
        for ui_section in ui_sections:
            ui_section.view = _ui_view.sys_id
            _ui_section = self.create_or_update_entry(ui_section)

            ui_form_section = ServiceNowDatamodels.SNUiFormSection(
                sys_ui_form=_ui_form.sys_id,
                sys_ui_section=_ui_section.sys_id,
                position=ui_section.position,
            )
            _ui_form_section = self.create_or_update_entry(ui_form_section)

            # Populate section with defined fields
            for section_field in ui_section.section_fields:
                section_field.sys_ui_section = _ui_section.sys_id
                _section_field = self.create_or_update_entry(section_field)

        return _ui_view

    def get_list_ui_view_fields(
        self, list_id: str
    ) -> list[ServiceNowDatamodels.SNUiListElement]:
        """
        Get all UI List elements for specified list_id.

        Params:
            list_id: Sys ID for the list elements to be fetched for
        """
        uri = self._get_full_url("get_ui_list_elements", list_id=list_id)

        response = self.session.get(uri)
        self.validate_response(response)

        return [
            self.parser.parse_sn_entry(
                ServiceNowDatamodels.SNUiListElement, element_data
            )
            for element_data in response.json()["result"]
        ]

    def clear_list_ui_view_fields(self, list_id: str, exclude_list: list[str]) -> None:
        """
        Remove all extra UI List elements.

        Params:
            list_id: Sys ID for the list to be updated
            exclude_list: List of fields excluded for removal
        """

        try:
            list_ui_elements = self.get_list_ui_view_fields(list_id)
        except SNowNotFoundException:
            # If there are already no fields, no need to clear anything out
            return

        for list_ui_element in list_ui_elements:
            if list_ui_element.element in exclude_list:
                continue

            table_uri = self._get_full_url("tables", table=list_ui_element.table_name)
            response = self.session.delete(f"{table_uri}/{list_ui_element.sys_id}")
            self.validate_response(response, force_json_result=False)

    def create_list_ui_view(
        self,
        ui_view: ServiceNowDatamodels.SNUiView,
        ui_list: ServiceNowDatamodels.SNUiList,
    ) -> ServiceNowDatamodels.SNUiView:
        """
        Create List UI View with given UI view and UI List data models.

        Params:
            ui_view: data model representing a UI view
            ui_list: data model representing a UI list (with UI element list)

        Returns:
            SNUiView data model parsed from create view request
        """
        # First we need to create (or fetch) an ui view and ui_list linked to it
        _ui_view = self.create_or_update_entry(ui_view)
        ui_list.view = _ui_view.sys_id
        _ui_list = self.create_or_update_entry(ui_list)

        # Second step would be to create UI list elements iterating through
        # list_fields attr
        self.clear_list_ui_view_fields(
            list_id=_ui_list.sys_id,
            exclude_list=[element.element for element in ui_list.list_fields],
        )
        for ui_list_element in ui_list.list_fields:
            ui_list_element.list_id = _ui_list.sys_id
            self.create_or_update_entry(ui_list_element)

        return _ui_view

    @staticmethod
    def __build_system_query(
        query_fragments: Iterable[str], join_char: str = "^"
    ) -> str:
        """
        Join query fragments
        :param query_fragments {list}
        :param join_char {str} char for join fragments
        :return: {str} query string
        """
        return join_char.join(query_fragments)

    @staticmethod
    def __get_param_query_fragment(
        key: str, values: Iterable[str], operator: str = "=", join_char: str = "^"
    ) -> str:
        """
        Generate query fragment
        :param key {str} query key
        :param values {list} List of query values
        :param operator {str} operator between key nad value
        :param join_char {str} char for join fragment
        """
        return join_char.join([f"{key}{operator}{fragment}" for fragment in values])
