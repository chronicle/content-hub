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
from typing import Union
import requests
from urllib.parse import urljoin
from copy import deepcopy
from . import datamodels
from .AzureADParser import AzureADParser
from .exceptions import AzureADError, AzureADNotFoundError, AzurePasswordComplexityError
from .utils import sanitize_odata_filter_value
from .constants import ALL_FIELDS_IDENTIFIER, DEFAULT_API_ROOT, DEFAULT_LOGIN_API_ROOT, SELECT_ONE_FILTER_KEY, NOT_FOUND_ERROR_CODE, FORBIDDEN_ERROR_CODE, NO_CONTENT_STATUS_CODE


DEFAULT_ORDER_BY = "ASC"
DEFAULT_ORDER_BY_FIELD = "displayName"
GRANT_TYPE = "client_credentials"
TOKEN_PAYLOAD = {
    "client_id": None,
    "scope": None,
    "client_secret": None,
    "grant_type": GRANT_TYPE,
}
DEFAULT_SCOPE = ".default"
OAUTH_TOKEN_PATH = "/oauth2/v2.0/token"
DIRECTORY_OBJECT_PATH = "v1.0/directoryObjects/{}"

LIST_OF_USERS_ORDER = "$orderby={}%20{}&$select={}"
LIST_OF_GROUPS_ORDER = "$orderby={}%20{}"
DEVICES_FILTER = "$filter=displayName%20eq%20'{}'"
USER_IN_GROUP = "$filter=id%20eq%20'{}'"
ENABLE_USER_ACCOUNT = {"accountEnabled": "true"}
DISABLE_USER_ACCOUNT = {"accountEnabled": "false"}
FORCE_PASSWORD_UPDATE = {"passwordProfile": {"forceChangePasswordNextSignIn": "true"}}

MANAGER_DEFAULT_FIELDS = ["displayName", "mobilePhone", "mail"]

API_ENDPOINTS = {
    "ping": "/v1.0",
    "users": "v1.0/users",
    "user": "v1.0/users/{user}",
    "group_users": "v1.0/groups/{group_id}/members/$ref",
    "user_member_of": "v1.0/users/{user}/memberOf",
    "manager": "v1.0/users/{user}/manager",
    "groups": "v1.0/groups",
    "devices": "v1.0/devices",
    "remove_user_from_group": "v1.0/groups/{group_id}/members/{user_id}/$ref",
    "list_user_groups": "v1.0/users/{username}/getMemberGroups",
    "group_members_details": "v1.0/groups/{group_id}/members",
    "revoke_user_session": "v1.0/users/{user_id}/revokeSignInSessions",
    "user_registration_details": (
        "beta/reports/authenticationMethods/userRegistrationDetails"
    ),
}


class AzureADManager:
    def __init__(
        self,
        client_id,
        client_secret,
        tenant,
        verify_ssl,
        api_root=DEFAULT_API_ROOT,
        login_api_root=DEFAULT_LOGIN_API_ROOT,
        force_check_connectivity=False,
    ):
        self.api_root = api_root.rstrip("/") + "/"
        self.login_api_root = login_api_root.rstrip("/") + "/"
        self.client_id = client_id
        self.client_secret = client_secret
        self.tenant = tenant
        self.session = requests.Session()
        self.session.verify = verify_ssl
        self.access_token = self.generate_token(
            self.client_id, self.client_secret, self.tenant
        )
        self.session.headers.update(
            {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json",
            }
        )
        self.parser = AzureADParser()

        if force_check_connectivity:
            self.test_connectivity()

    def generate_token(self, client_id, client_secret, tenant):
        """
        Request access token (Valid for 60 min)
        :param client_id: {string} The Application ID that the registration portal
        :param client_secret: {string} The application secret that you created in the app registration portal for your app.
        :param tenant: {string} Tenant or also called directory ID
        :return: {string} Access token. The app can use this token in calls to Microsoft Graph.
        """
        payload = deepcopy(TOKEN_PAYLOAD)
        payload["client_id"] = client_id
        payload["client_secret"] = client_secret
        payload["scope"] = urljoin(self.api_root, DEFAULT_SCOPE)
        token_url = urljoin(self.login_api_root, f"{tenant}{OAUTH_TOKEN_PATH}")
        res = self.session.post(token_url, data=payload)
        self.validate_response(res)
        return res.json().get("access_token")

    def _get_full_url(self, url_id, **kwargs):
        """
        Get full url from url identifier
        :param url_id: {str} the id of url
        :param kwargs: {dict} variables passed for string formatting
        :return: {str} the full url
        """
        encoded_kwargs = {key: requests.utils.quote(str(value), safe="")
                          for key, value in kwargs.items()}
        return urljoin(self.api_root, API_ENDPOINTS[url_id].format(**encoded_kwargs))

    @staticmethod
    def validate_response(
        response,
        error_msg="An error occurred",
        validate_azure_status=False,
        handle_404=False,
        check_message=False,
    ):

        try:
            response.raise_for_status()
        except requests.HTTPError as error:
            try:
                response.json()
            except:
                raise AzureADError(f"{error_msg}: {error} - {response.content}")

            if handle_404 and response.status_code == NOT_FOUND_ERROR_CODE:
                raise AzureADNotFoundError
            if check_message:
                message = response.json().get("error", {}).get("message", "")
                expected_error_message = (
                    "The specified password does not comply with password complexity "
                    "requirements. Please provide a different password."
                )
                if message == expected_error_message:
                    raise AzurePasswordComplexityError(
                        f"{error_msg}: {error} - {response.json().get('error', 'No error message.')}"
                    )
            raise AzureADError(
                f"{error_msg}: {error} - {response.json().get('error', 'No error message.')}"
            )
        if validate_azure_status and not response.status_code == NO_CONTENT_STATUS_CODE:
            raise AzureADError(f"{error_msg} - please check the logs.")

    def get_list_of_users(
        self,
        filter_field,
        filter_value,
        filter_logic,
        order_by=DEFAULT_ORDER_BY,
        order_by_field=DEFAULT_ORDER_BY_FIELD,
        limit=None,
    ):
        """
        Function that requests a list of all users from the AzureAD
        :param filter_field: {string} A single value which specifies the user fields returned from the AzureAD
        :param filter_value: {string} What value should be used in the filter
        :param filter_logic: {string} What filter logic should be applied.
        :param order_by: {string} DESC or ASC keywords to specify the order of the results
        :param order_by_field: {string} Field name on based on which the order is done
        :param limit: {int} Max number of results to return
        :return: {List} List of users
        """
        if filter_field == ALL_FIELDS_IDENTIFIER:
            filter_field = ""

        url = self._get_full_url("users")
        additional_params = LIST_OF_USERS_ORDER.format(
            order_by_field, order_by, filter_field
        )

        return self._paginate_results(
            url=url,
            parser_method="build_siemplify_user_list",
            params=additional_params,
            limit=limit,
            err_msg="Unable to get list of users from Azure Active Directory, please check the connection.",
            filter_value=filter_value,
            filter_logic=filter_logic,
        )

    def get_group_members(
        self, filter_key, filter_value, filter_logic, group_id, limit=None
    ):
        """
        Function that requests a list of group members
        :param filter_key: {string} What filter key should be applied.
        :param filter_value: {string} What value should be used in the filter
        :param filter_logic: {string} What filter logic should be applied.
        :param limit: {int} Max number of results to return
        :return: {List} List of group members
        """

        if filter_key == SELECT_ONE_FILTER_KEY:
            filter_key = ""

        url = self._get_full_url("group_members_details", group_id=group_id)

        return self._paginate_results(
            url=url,
            parser_method="build_group_members_list",
            params=None,
            limit=limit,
            err_msg="Unable to get list of users from Azure Active Directory, please check the connection.",
            filter_value=filter_value,
            filter_logic=filter_logic,
            filter_key=filter_key,
        )

    def get_list_of_groups(self, filter_value, filter_logic, order_by, limit=None):
        """
        Function that requests a list of all groups from the AzureAD
        :param order_by: {string} DESC or ASC keywords to specify the order of the results
        :param filter_value: {string} What value should be used in the filter
        :param filter_logic: {string} What filter logic should be applied.
        :return: {List} List of groups
        """
        url = self._get_full_url("groups")
        additional_params = LIST_OF_GROUPS_ORDER.format(
            DEFAULT_ORDER_BY_FIELD, order_by
        )
        return self._paginate_results(
            url=url,
            parser_method="build_siemplify_group_list",
            params=additional_params,
            limit=limit,
            err_msg="Unable to get list of groups from Azure Active Directory, please check the connection.",
            filter_value=filter_value,
            filter_logic=filter_logic,
        )

    def get_list_of_all_groups(self):
        """
        Function that requests a list of all groups from the AzureAD
        :return: {List} List of groups
        """
        url = self._get_full_url("groups")
        return self._paginate_results(
            url=url,
            parser_method="build_siemplify_group_list",
            limit=None,
            err_msg="Unable to get list of groups from Azure Active Directory, please check the connection.",
        )

    def get_group_by_name(self, group_name: str) -> datamodels.Group | None:
        """
        Retrieve a group from Azure AD by its name (displayName or mailNickname).

        Args:
            group_name: The display name or mail nickname of the group.

        Returns:
            datamodels.Group: A Group data model object if found, otherwise None.
        """
        sanitized_group_name = sanitize_odata_filter_value(group_name)

        params = {
            "$filter": (
                f"displayName eq '{sanitized_group_name}' or "
                f"mailNickname eq '{sanitized_group_name}'"
            ),
            "$select": "id,displayName,mailNickname"
        }

        url = self._get_full_url("groups")
        response = self.session.get(url, params=params)
        self.validate_response(
            response, f"Unable to find group by name {group_name}"
        )

        if results := response.json().get("value", []):
            return self.parser.build_siemplify_group_object(results[0])

        return None

    def enable_user(self, user_principal_name):
        """
        Function that enables used in the AzureAD
        :param user_principal_name: {string} User's principal name
        """
        payload = {"accountEnabled": "true"}
        response = self.session.patch(
            self._get_full_url("user", user=user_principal_name), json=payload
        )
        self.validate_response(
            response,
            f"Unable to enable the user {user_principal_name} in Azure Active Directory, please check the "
            f"connection. ",
            validate_azure_status=True,
        )

    def disable_user(self, user_principal_name):
        """
        Function that disables used in the AzureAD
        :param user_principal_name: {string} User's principal name
        """
        payload = {"accountEnabled": "false"}
        response = self.session.patch(
            self._get_full_url("user", user=user_principal_name), json=payload
        )
        self.validate_response(
            response,
            f"Unable to disable the user {user_principal_name} in Azure Active Directory, please check the "
            f"connection.",
            validate_azure_status=True,
        )

    def get_user(
        self, user_principal_name: str, fields_to_return: Union[str, None] = None
    ) -> datamodels.User:
        """Function that enriches the USER entity

        Args:
            user_principal_name: User's principal name
            fields_to_return: Comma-separated string of fields to return
        Returns:
            User object containing enrichment data for an user
        """
        params = {}
        if fields_to_return:
            params["$select"] = fields_to_return

        url = self._get_full_url("user", user=user_principal_name)
        response = self.session.get(url, params=params)
        self.validate_response(
            response,
            f"Unable to enrich the user: {user_principal_name} in Azure Active Directory.",
        )

        return self.parser.build_siemplify_user_object(response.json())

    def get_user_registration_details(self, user_principal_name: str) -> dict:
        """
        Get MFA registration details for a user.
        Args:
            user_principal_name: User's principal name
        Returns:
            dict: MFA registration details
        """
        sanitized_upn = sanitize_odata_filter_value(user_principal_name)
        params = {"$filter": f"userPrincipalName eq '{sanitized_upn}'"}
        url = self._get_full_url("user_registration_details")
        response = self.session.get(url, params=params)

        try:
            self.validate_response(
                response,
                "Unable to get MFA registration details for user: "
                f"{user_principal_name}",
            )
        except AzureADError as e:
            # AuditLog.Read.All is required (403).
            # Beta endpoint might be removed or changed (404).
            # In both cases, return empty dict to not break the main enrichment action.
            if response.status_code in [FORBIDDEN_ERROR_CODE, NOT_FOUND_ERROR_CODE]:
                return {}
            raise e

        return self.parser.build_user_registration_details(response.json())

    def get_host(self, hostname):
        """
        Function that enriches the HOSTNAME entity
        :param hostname: {string} hostname that will be enriched, called device in AzureAD
        :return: {Host} Host object containing enrichment data for a host
        """
        sanitized_hostname = sanitize_odata_filter_value(hostname)
        response = self.session.get(
            self._get_full_url("devices"),
            params=DEVICES_FILTER.format(sanitized_hostname)
        )
        self.validate_response(
            response,
            f"Unable to enrich the host: {hostname} in Azure Active Directory.",
        )
        results = self.parser.get_host_values(response.json())
        if results:
            filtered_results = [host for host in results if host.account_enabled]
            return sorted(
                filtered_results, key=lambda filtered_host: filtered_host.last_sign_in
            )[-1]

        raise AzureADError(
            f"Hostname {hostname} was not found in the Azure Active Directory."
        )

    def force_password_update(self, user_principal_name):
        """
        Function that forces the password update based on user's principal name
        :param user_principal_name: {string} User's principal name
        """
        response = self.session.patch(
            self._get_full_url("user", user=user_principal_name),
            json=FORCE_PASSWORD_UPDATE,
        )
        self.validate_response(
            response,
            f"Unable to force the password update for user: {user_principal_name}.",
            validate_azure_status=True,
        )

    def reset_user_password(self, user_principal_name, new_password):
        """
        Function that sets new password for a user based on user's principal name
        :param user_principal_name: {string} User's principal name
        :param new_password: {string} New password set for the user
        """
        payload = {
            "passwordProfile": {
                "forceChangePasswordNextSignIn": "true",
                "password": new_password,
            }
        }

        response = self.session.patch(
            self._get_full_url("user", user=user_principal_name), json=payload
        )
        self.validate_response(
            response,
            f"Unable to reset password for user: {user_principal_name}.",
            validate_azure_status=True,
            check_message=True,
        )

    def check_user_in_group(self, user_principal_name, group_id):
        """
        Function that checks if an user is a member of a group.
        :param user_principal_name: {string} User's principal name
        :param group_id: {string} Group ID that identifies the group
        :return: {Bool} True is the user is a member of the group False otherwise
        """
        params = USER_IN_GROUP.format(sanitize_odata_filter_value(group_id))
        response = self.session.get(
            self._get_full_url("user_member_of", user=user_principal_name),
            params=params,
        )
        self.validate_response(
            response,
            f"Unable to check if user {user_principal_name} is in group {group_id}.",
        )

        return self.parser.check_is_user_member_of(response.json())

    def get_user_id(self, user_principal_name):
        """
        Function that gets user's ID based on the user principal name
        :param user_principal_name: {string} User's principal name
        :return: {string} user's ID in AZureAD
        """
        response = self.session.get(
            self._get_full_url("user", user=user_principal_name)
        )
        self.validate_response(
            response, f"Unable to get the ID of the user {user_principal_name}."
        )

        return self.parser.user_id_based_on_name(response.json())

    def get_user_id_with_filter(self, user_identifier, filter_keys):
        """
        Get user id by either user name or email
        :param user_identifier: {str} user name or email
        :param filter_keys: {list} displayName or mail
        :return: {string} user id if exist
        """
        url = self._get_full_url("users")

        if not filter_keys:
            raise AzureADError("Filter keys are not provided.")

        sanitized_user_identifier = sanitize_odata_filter_value(user_identifier)

        filter_string = " or ".join(
            f"{filter_key} eq '{sanitized_user_identifier}'"
            for filter_key in filter_keys
        )

        params = {"$filter": filter_string}
        response = self.session.get(url, params=params)
        self.validate_response(response)

        users = response.json().get("value")

        for user in users:
            user_has_desired_attribute = any(
                user.get(filter_key)
                and user.get(filter_key).casefold() == user_identifier.casefold()
                for filter_key in filter_keys
            )
            if user_has_desired_attribute:
                return user.get("id")

        raise AzureADNotFoundError("User not found")

    def revoke_user_session(self, user_id):
        """
        Revoke user session
        :param user_id: {str} Id of the user
        """
        url = self._get_full_url("revoke_user_session", user_id=user_id)
        response = self.session.post(url)
        self.validate_response(response)

        return response.json()

    def add_user_to_group(self, group_id, user_principal_name):
        """
        Function that adds an user to the group
        :param user_principal_name: {string} User's principal name
        :param group_id: {string} Group ID that identifies the group
        """
        directory_object = urljoin(self.api_root, DIRECTORY_OBJECT_PATH)
        payload = {
            "@odata.id": directory_object.format(self.get_user_id(user_principal_name))
        }
        response = self.session.post(
            self._get_full_url("group_users", group_id=group_id), json=payload
        )
        self.validate_response(
            response,
            f"Unable to add user {user_principal_name} to the group {group_id}.",
            validate_azure_status=True,
        )

    def remove_user_from_group(self, group_id, user_id):
        """
        Function that removes the user from the group
        :param user_id: {string} User's ID
        :param group_id: {string} Group ID that identifies the group
        """
        request_url = self._get_full_url(
            "remove_user_from_group", group_id=group_id, user_id=user_id
        )
        response = self.session.delete(request_url)
        self.validate_response(
            response,
            "Unable to remove user from the group.",
            validate_azure_status=True,
            handle_404=True,
        )

    def get_group_id(self, group_name):
        """
        Function that gets group's ID based on the group name
        :param group_name: {string} Group's name
        :return: {string} group's ID in AZureAD
        """
        request_url = self._get_full_url("groups")
        groups = self._paginate_results(
            url=request_url,
            parser_method="build_siemplify_group_list",
            err_msg="Unable to get list of groups from Azure Active Directory, "
                    "please check the connection.",
        )

        return next((group.id for group in groups if group.name == group_name), None)

    def get_user_groups(self, username, only_security_enabled_groups, limit=None):
        """
        Get user groups by username
        :param username: {str} username to get groups for
        :param only_security_enabled_groups: {bool} specifies if only security groups that the user is a member should be returned
        :param limit: {int} limit for results
        :return: {list} list of Group objects
        """
        url = self._get_full_url("list_user_groups", username=username)
        payload = {"securityEnabledOnly": only_security_enabled_groups}

        response = self.session.post(url, json=payload)
        self.validate_response(response)
        return (
            response.json().get("value", [])[:limit]
            if limit
            else response.json().get("value", [])
        )

    def test_connectivity(self):
        """
        Function that checks the connection to the AzureAD
        """
        response = self.session.get(self._get_full_url("ping"))
        self.validate_response(response, "Unable to connect to Azure Active Directory")

    def get_users_manager(self, user_principal_name, fields_to_return=None):
        """
        Function that gets manager information.
        :param user_principal_name: {string} User's principal name
        :param fields_to_return: {list} List of fields to return
        :return {User} information about the manager
        """
        params = {}
        fields_list = list(fields_to_return or [])
        if not fields_list:
            fields_list = MANAGER_DEFAULT_FIELDS

        if "sponsors" in fields_list:
            fields_list.remove("sponsors")
            params["$expand"] = "sponsors"

            if not fields_list:
                fields_list = MANAGER_DEFAULT_FIELDS

        if fields_list:
            params["$select"] = ",".join(fields_list)

        base_url = self._get_full_url("manager", user=user_principal_name)

        if params.get("$expand") == "sponsors":
            url = f"{base_url}/microsoft.graph.user"
        else:
            url = base_url

        response = self.session.get(url, params=params)

        if response.status_code == NOT_FOUND_ERROR_CODE:
            raise AzureADNotFoundError(
                f"Manager not found for user {user_principal_name}"
            )

        self.validate_response(
            response,
            f"Unable to get manager information for "
            f"user {user_principal_name}."
        )

        manager_data = response.json()
        return self.parser.build_users_manager_object(manager_data)

    def enrich_manager_with_mfa(self, user_principal_name, user_manager, logger=None):
        """
        Enrich manager object with MFA details
        :param user_principal_name: {string} User's principal name
        :param user_manager: {Manager} Manager object
        :param logger: {SiemplifyLogger} Logger object
        """
        user_supervisor_name = self.get_users_manager(
            user_principal_name=user_principal_name,
            fields_to_return=["userPrincipalName"]
        )

        if user_supervisor_name.username:
            mfa_details = self.get_user_registration_details(
                user_supervisor_name.username
            )
            user_manager.set_mfa_details(mfa_details)
        elif logger:
            logger.error(
                f"Manager found for user {user_principal_name}, "
                "but 'userPrincipalName' is missing. "
                "Cannot fetch MFA details."
            )

    @staticmethod
    def validate_azure_status(response, error_message):
        """
        Function that validates the response from AzureAD, successful action resturns HTTP Code 204, everything else is considered as fail
        :param response: {Response} Raw response from the AzureAD
        :param error_message: {string} Error message used in the exception
        """
        if not response.status_code == NO_CONTENT_STATUS_CODE:
            raise AzureADError(error_message)

    def _paginate_results(
        self,
        url,
        parser_method,
        method=None,
        params=None,
        body=None,
        limit=None,
        err_msg=None,
        filter_value=None,
        filter_logic=None,
        filter_key=None,
    ):
        """
        Paginate the results of a job
        :param method: {str} The method of the request (GET, POST, PUT, DELETE, PATCH)
        :param url: {str} The url to send request to
        :param parser_method: {str} The name of parser method to build the result
        :param params: {dict} The params of the request
        :param body: {dict} The json payload of the request
        :param limit: {int} The limit of the results to fetch
        :param err_msg: {str} The message to display on error
        :param filter_value: {string} What value should be used in the filter
        :param filter_logic: {string} What filter logic should be applied.
        :param filter_key: {string} What filter key should be applied.
        :return: {list} List of results
        """
        method = method or "GET"
        err_msg = err_msg or "Unable to get results"
        params = params or {}

        response = self.session.request(method, url, params=params, json=body)

        self.validate_response(response, err_msg)
        results = getattr(self.parser, parser_method)(
            raw_data=response.json(),
            filter_value=filter_value,
            filter_logic=filter_logic,
            filter_key=filter_key,
        )
        while True:
            if limit and len(results) >= limit:
                break

            if not self.parser.get_page_next_link(response.json()):
                break

            response = self.session.request(
                method, self.parser.get_page_next_link(response.json())
            )
            self.validate_response(response, err_msg)
            results.extend(
                getattr(self.parser, parser_method)(
                    raw_data=response.json(),
                    filter_value=filter_value,
                    filter_logic=filter_logic,
                    filter_key=filter_key,
                )
            )
        return results[:limit] if limit else results
