# ============================================================================#
# title           :GSuiteManager.py
# description     :This Module contain all GSuite operations functionality
# author          :gabriel.munits@siemplify.co (refactored)
# date            :11-02-2020
# python_version  :3.7
# libraries       :requests
# requirements     :
# product_version :
# ============================================================================#

# HOW TO OBTAIN REFRESH TOKEN
# 1. Follow the instructions at the following link to enable Directory API and
# create OAuth client id and secret.
# https://developers.google.com/admin-sdk/directory/v1/get-start/getting-started
#
# 2. Using the generated client id and secret and selected redirect url use the
# Get Authorization action to generate an authorization url. Open the link and
# allow access to the needed scopes (must be done as a GSuite admin)
#
# 3. After completing the authorization, copy the url you were redirected to
# and use the Generate Token action to generate a refresh token. If the action
# resulted in an empty (None) refresh token, go to the link below:
# https://myaccount.google.com/u/0/permissions
# And remove the app permissions and repeat hte steps above.
#
# 4. Using the generated refresh token, configure the integration. Notice that
# the token is time limited and you will need to repeat the process in the
# future.

# ============================= IMPORTS ===================================== #
from __future__ import annotations
import json
import crypt
from typing import Optional, Any
import requests
from urllib.parse import urljoin

from google.auth.transport.requests import AuthorizedSession

from TIPCommon.base.interfaces import Apiable
from TIPCommon.types import SingleJson
from g_suite.core import consts
from g_suite.core import datamodels
from g_suite.core import utils
from g_suite.core.GSuiteParser import GSuiteParser
from g_suite.core.consts import INTEGRATION_NAME, API_ROOT, ENDPOINTS
from g_suite.core.exceptions import (
    GSuiteManagerError,
    GSuiteEntityExistsException,
    GSuiteNotFoundException,
    GSuiteValidationException,
)


# ============================= CLASSES ===================================== #


class GSuiteManager(Apiable):

    def __init__(
        self, session: AuthorizedSession, params: datamodels.IntegrationParameters
    ):
        self.session = session
        self.parser = GSuiteParser()

        self.api_root = API_ROOT
        self.logger = params.siemplify_logger

    def _get_full_url(
        self,
        url_key: str,
        base_url: str | None = None,
        **kwargs: Any,
    ) -> str:
        """
        Get the full URL for a given API endpoint.

        This method constructs the full URL by joining a base URL with a
        relative path from the ENDPOINTS constant. It can use a provided
        base_url or fall back to the default self.api_root.

        Args:
            url_key (str): The key corresponding to the endpoint's path in
                the ENDPOINTS dictionary.
            base_url (str | None): The base URL for the request. If not
                provided, the default `self.api_root` will be used.
            **kwargs (Any): Keyword arguments to format the endpoint path string.

        Returns:
            str: The complete, formatted URL for the API endpoint.
        """
        root: str = base_url or self.api_root
        return urljoin(root, ENDPOINTS[url_key].format(**kwargs))

    def test_connectivity(self):
        """
        Test connectivity with GSuite
        :return: raise Exception if failed to validate response
        """
        connectivity_err_msg = f"Unable to test connectivity with {INTEGRATION_NAME}"

        request_url = self._get_full_url("list-users")
        response = self.session.get(
            request_url, params={"maxResults": 1, "customer": "my_customer"}
        )
        self.validate_response(response, error_msg=connectivity_err_msg)

    def get_user(self, primary_email: str) -> datamodels.User:
        """
        Retrieves a user.
        :param primary_email: {str} Identifies the user in the API request. The value can be the user's primary email address,
        alias email address, or unique user ID.
        :return: {datamodels.User}
        """
        request_url = self._get_full_url("get-user", primary_email=primary_email)
        response = self.session.get(request_url)
        self.validate_response(
            response, error_msg=f"Failed to get user with email {primary_email}"
        )
        return self.parser.build_user_obj(response.json())

    def create_user(
        self,
        given_name: str,
        family_name: str,
        password: str,
        primary_email: str,
        change_password_at_next_login: Optional[bool] = False,
        phone: Optional[str] = None,
        organization: Optional[str] = None,
        department=None,
        gender: Optional[str] = None,
        note: Optional[str] = None,
    ) -> datamodels.User:
        """
        Create a new user
        :param given_name: {str} The user's first name. Required when creating
            a user account.
        :param family_name: {str} The user's last name. Required when creating
            a user account.
        :param password: {str} Stores the password for the user account.
            The user's password value is required when creating a user account.
            It is optional when updating a user and should only be provided if
            the user is updating their account password.
            A password can contain any combination of ASCII characters.
            A minimum of 8 characters is required. The maximum length is
            100 characters.
        :param primary_email: {str} The user's primary email address.
            This property is required in a request to create a user account.
            The primaryEmail must be unique and cannot be an alias of another
            user.
        :param phone: {str} User's phone number.
        :param organization: {str} Organization user belongs to.
        :param department: {str} Department user belongs to.
        :param change_password_at_next_login: {bool} Whether demand the user
            to change his password at next login
        :param gender: {str} The gender of the user. Insensitive capitalization. Valid values:
            - female
            - male
            - other
            - unknown
        :param note: {str} Note to add to the user.
        :return: {datamodels.User} user datamodel. Exception if failed to validate response
        """
        request_url = self._get_full_url("create-user")

        payload = {
            "name": {"familyName": family_name, "givenName": given_name},
            "password": crypt.crypt(password, crypt.METHOD_SHA256),
            "hashFunction": consts.SHA256_HASH_FUNCTION,
            "primaryEmail": primary_email,
            "notes": {"value": note} if note else {},
            "changePasswordAtNextLogin": change_password_at_next_login,
            "phones": [{"value": phone}] if phone else [],
            "gender": {"type": gender.lower()} if gender else {},
            "organizations": (
                [
                    {
                        "name": organization if organization else "",
                        "department": department if department else "",
                    }
                ]
                if organization or department
                else []
            ),
        }
        response = self.session.post(
            request_url, json=utils.remove_empty_kwargs(**payload)
        )
        self.validate_response(
            response, f"Unable to create user with email {primary_email}"
        )
        return self.parser.build_user_obj(response.json())

    def update_user(
        self,
        primary_email: str,
        given_name: Optional[str] = None,
        family_name: Optional[str] = None,
        password: Optional[str] = None,
        change_password_at_next_login=False,
        phone: Optional[str] = None,
        organization: Optional[str] = None,
        department: Optional[str] = None,
        gender=None,
        suspended: bool = None,
    ) -> datamodels.User:
        """
        Update a user
        :param given_name: {str} The user's first name.
        :param family_name: {str} The user's last name.
        :param password: {str} Stores the password for the user account.
            The user's password value is required when creating a user account.
            It is optional when updating a user and should only be provided if
            the user is updating their account password.
            A password can contain any combination of ASCII characters.
            A minimum of 8 characters is required. The maximum length is
            100 characters.
        :param primary_email: {str} The user's primary email address.
            This property is required in a request to update a user account.
            The primaryEmail must be unique and cannot be an alias of another
            user.
        :param phone: {str} User's updated phone number.
        :param organization: {str} Updated organization the user belongs to.
        :param department: {str} Updated department the user belongs to.
        :param change_password_at_next_login: {bool} Whether demand the user
            to change his password at next login
        :param gender: {str} Gender of the user. Insensitive capitalization. Valid values are:
            - female
            - male
            - other
            - unknown
        :param suspended: {bool} Whether the user account suspended or not
        :return: {datamodels.User} User datamodel. Exception if failed to validate response
        """
        request_url = self._get_full_url("update-user", primary_email=primary_email)

        payload = {
            "name": (
                {"familyName": family_name, "givenName": given_name}
                if family_name and given_name
                else {}
            ),
            "password": (
                crypt.crypt(password, crypt.METHOD_SHA256) if password else None
            ),
            "hashFunction": consts.SHA256_HASH_FUNCTION if password else None,
            "primaryEmail": primary_email,
            "changePasswordAtNextLogin": change_password_at_next_login,
            "phones": [{"value": phone}] if phone else [],
            "gender": {"type": gender.lower()} if gender else {},
        }

        if family_name:
            payload["name"]["familyName"] = family_name
        if given_name:
            payload["name"]["givenName"] = given_name
        if suspended is not None:
            payload["suspended"] = suspended

        organization_payload = {}
        if department:
            organization_payload["department"] = department
        if organization:
            organization_payload["name"] = organization

        if organization or department:
            payload["organizations"] = [organization_payload]

        response = self.session.put(
            request_url, json=utils.remove_empty_kwargs(**payload)
        )
        self.validate_response(
            response, f"Unable to update user with email {primary_email}"
        )
        return self.parser.build_user_obj(response.json())

    def delete_user(self, primary_email: str):
        """
        Delete a user
        :param primary_email: {str} The user's primary email address (unique)
        :return: raise GSuiteManagerError if failed to validate response
            raise GSuiteNotFoundException if user was not found
        """
        request_url = self._get_full_url("delete-user", primary_email=primary_email)
        res = self.session.delete(request_url)
        self.validate_response(res, f"Unable to delete user {primary_email}")

    def sign_out_user(self, primary_email: str) -> None:
        """Sign out a user.

        Args:
            primary_email: {str} The user's primary email address (unique)

        Raises:
            GSuiteManagerError if failed to validate response
            GSuiteNotFoundException if user was not found
        """
        request_url = self._get_full_url("sign-out-user", primary_email=primary_email)
        res = self.session.post(request_url)
        self.validate_response(res, f"Unable to sign out user {primary_email}")

    def _map_query_params(self, param: Any):
        """
        Map query parameters
        :param param: {str} the param to map into the query
        :return: {str} mapped param
        """
        query_param_mapper = {
            "bool": utils.map_boolean_query_param,
            "str": utils.map_str_query_param,
        }
        return query_param_mapper.get(type(param).__name__, lambda f: f)(param)

    def _query_builder(
        self,
        clauses_operator: Optional[str] = consts.AND,
        inclause_operator: Optional[str] = consts.EQUAL,
        **kwargs,
    ):
        """
        Returns query build for kwargs with an operator
        :param clauses_operator: {str} operator to join clauses (**kwargs)
        :param inclause_operator: {str} operator to join literals inside the each clause
        :param kwargs:  {dict} dictionary containing key values. Values must not be iterables unless it's a concrete string
        :return: {str} query built for provided parameters
        """
        return f"{clauses_operator}".join(
            f"{k}{inclause_operator}{self._map_query_params(v)}"
            for k, v in kwargs.items()
        )

    def list_users(
        self,
        limit: Optional[int] = None,
        customer_id: Optional[str] = None,
        domain: Optional[str] = None,
        order_by: Optional[str] = "givenName",
        show_deleted: Optional[bool] = None,
        manager_email: Optional[str] = None,
        only_admin_accounts: Optional[bool] = None,
        only_delegated_admin_accounts: Optional[bool] = None,
        only_suspended_users: Optional[bool] = None,
        org_unit_path: Optional[str] = None,
        department: Optional[str] = None,
        custom_query: Optional[str] = None,
        only_without_2fa: Optional[bool] = None,
        email_addresses: Optional[list] = None,
    ) -> [datamodels.User]:
        """List users in a domain

        Args:
            limit: Specify how many records can be returned by the action.
            customer_id: The unique ID for the customer's Google Workspace account.
                In case of a multi-domain account,
                to fetch all groups for a customer, fill this field instead of domain.
                You can also use the my_customer alias to represent your account's
                customerId.
                The customerId is also returned as part of the Users resource.
                Either the customer or the domain parameter must be provided.
            manager_email: The email address of a user's manager either directly or
                up the management chain.
            only_admin_accounts: True if to return only user admin accounts,
                otherwise False.
            only_delegated_admin_accounts: True if to return user accounts with
                delegated administrator privileges.
            only_suspended_users: True if to return user accounts that are suspended.
            org_unit_path: The full path of an organization unit. All users in
                the organization will be returned.
            department: The department to return users from.
            custome_query: Custom query to add the list-users query call.
                Additional information can be found here -
                https://developers.google.com/admin-sdk/directory/v1/guides/search-users
            order_by: Property to use for sorting results. Valid values:
                - email
                - familyName
                - givenName
            show_deleted: If set to true, retrieves the list of
                deleted users. Default is false.
            domain: The domain name. Use this field to get fields from only one
                domain. To return all domains for a customer account,
                use the customer query parameter instead. Either the customer or
                the domain parameter must be provided.
                In case of a multi-domain account, to fetch all groups for a customer,
                don't fill the domain field.
                The my_customer alias will represent the account's customerId.
                The customerId is also returned as part of the Users resource.
                Either the customer or the domain parameter must be provided.
            only_without_2fa: If enabled, action will only return users that don't
                have 2fa enabled.
            email_addresses: A comma-separated list of email addresses that need to
                be searched for.

        Returns:
            List of found users represented as User datamodels.
        """
        request_url = self._get_full_url("list-users")

        # Build base query, optimizing for conditions
        base_query_kwargs = {
            "directManager": manager_email,
            "orgUnitPath": org_unit_path,
            "orgDepartment": department,
        }
        if only_admin_accounts or only_delegated_admin_accounts or only_suspended_users:
            base_query_kwargs.update(
                {
                    "isAdmin": only_admin_accounts,
                    "isDelegatedAdmin": only_delegated_admin_accounts,
                    "isSuspended": only_suspended_users,
                    "isEnrolledIn2Sv": only_without_2fa,
                }
            )
        if only_without_2fa:
            base_query_kwargs.update({"isEnrolledIn2Sv": False})

        base_query = self._query_builder(
            clauses_operator=consts.SPACE,
            inclause_operator=consts.EQUAL,
            **utils.remove_empty_kwargs(**base_query_kwargs),
        )

        base_params = {
            "orderBy": order_by,
            "projection": "full",
            "viewType": "admin_view",
            "showDeleted": show_deleted,
            "customer": customer_id or "my_customer",
            "domain": domain if domain else None,
        }

        # Handle email filtering
        users_results = self._filter_emails(
            email_addresses, base_query, base_params, custom_query, request_url, limit
        )

        return [self.parser.build_user_obj(raw_user) for raw_user in users_results]

    def list_group_members(
        self, group_email_address: str, include_derived_membership=True
    ) -> [datamodels.Member]:
        """
        List members of a group
        :param group_email_address: {str} The email address of the group
        :param include_derived_membership: {bool} Whether to list indirect
            memberships.
        :return: {[datamodels.Member]} List of found members in a group
        """
        request_url = self._get_full_url(
            "list-group-members", group_email=group_email_address
        )
        params = {"includeDerivedMembership": include_derived_membership}
        raw_member_results = self._paginate_results(
            method="GET",
            url=request_url,
            results_key="members",
            params=params,
            error_msg=f"Unable to list members of group {group_email_address}",
        )
        return [
            self.parser.build_member_obj(raw_member)
            for raw_member in raw_member_results
        ]

    def add_member_to_group(
        self, group_email_address: str, primary_email_address: str
    ) -> datamodels.Member:
        """
        Add a member to given group
        :param group_email_address: {str} The email of the group
        :param primary_email_address: {str} The email of the member to add to
            the group
        :return: {datamodels.Member} added member datamodel.
            raise GSuiteEntityExistsException if member already exists
            raise GSuiteManagerError if failed to validate status code
        """
        request_url = self._get_full_url(
            "add-member-to-group", group_email=group_email_address
        )
        payload = {"email": primary_email_address}
        response = self.session.post(request_url, json=payload)
        self.validate_response(
            response,
            f"Unable to add {primary_email_address} to group {group_email_address}",
        )
        return self.parser.build_member_obj(response.json())

    def remove_member_from_group(
        self, group_email_address: str, primary_email_address: str
    ):
        """
        Remove a member from a given group
        :param group_email_address: {str} The email of the group
        :param primary_email_address: {str} The email of the member to remove
            from the group
        :return: raise GSuiteNotFoundException if member already exists
            raise GSuiteManagerError if failed to validate status code
            raise GSuiteNotFoundException / GSuiteValidateException if group or user was not found
        """
        request_url = self._get_full_url(
            "remove-member-from-group",
            group_email=group_email_address,
            email_address=primary_email_address,
        )
        response = self.session.delete(request_url)
        self.validate_response(
            response,
            f"Unable to remove {primary_email_address} \
            from group {group_email_address}",
        )

    def create_group(
        self, email: str, description: Optional[str] = None, name: Optional[str] = None
    ) -> datamodels.Group:
        """
        Create a new group
        :param email: {str} The group's email address. Must be unique.
        :param description: {str} An extended description to help users
            determine the purpose of a group.
        :param name: {str} The group's display name.
        :return: {datamodels.Group} created group datamodel. Exception if failed to validate response
        """
        request_url = self._get_full_url("create-group")
        payload = {"email": email, "description": description, "name": name}
        response = self.session.post(
            request_url, json=utils.remove_empty_kwargs(**payload)
        )
        self.validate_response(response, f"Unable to create group with email {email}")
        return self.parser.build_group_obj(response.json())

    def create_ou(
        self,
        name: Optional[str] = None,
        description: Optional[str] = None,
        parent_path: Optional[str] = None,
        customer_id="my_customer",
    ) -> datamodels.OrgUnit:
        """
        Create an organizational unit
        :param name: {str} The name of the new OU
        :param description: {str} The description of the OU
        :param parent_path: {str} The organizational unit's parent path.
            For example, /corp/sales is the parent path for
            /corp/sales/sales_support organizational unit.
        :param customer_id: {str} The unique ID for the customer's G Suite
            account. As an account administrator, you can also use the
            my_customer alias to represent your account's customerId.
        :return: {datamodels.OrgUnit} created organization unit datamodel. Exception if failed to validate response
        """
        request_url = self._get_full_url("create-ou", customer_id=customer_id)

        payload = {
            "name": name,
            "description": description,
            "parentOrgUnitPath": parent_path,
        }

        response = self.session.post(
            request_url, json=utils.remove_empty_kwargs(**payload)
        )
        self.validate_response(
            response, f"Unable to create OU for customer id {customer_id}"
        )
        return self.parser.build_ou_obj(response.json())

    def update_ou(
        self,
        customer_id: str,
        path: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
    ) -> datamodels.OrgUnit:
        """
        Update an organizational unit
        :param path: {str} The full path to the organizational unit.
        :param customer_id: {str} The unique ID for the customer's G Suite
            account. As an account administrator, you can also use the
            my_customer alias to represent your account's customerId.
        :param name: {str} The name of the new OU
        :param description: {str} The description of the OU
        :return: {datamodels.OrgUnit} updated organization unit datamodel. Exception if failed to validate response
        """
        request_url = self._get_full_url(
            "update-ou", customer_id=customer_id, path=path
        )
        payload = {"name": name, "description": description}
        response = self.session.put(
            request_url, json=utils.remove_empty_kwargs(**payload)
        )
        self.validate_response(
            response, f"Unable to update OU for customer id {customer_id}"
        )
        return self.parser.build_ou_obj(response.json())

    def list_ou(
        self,
        customer_id: str,
        org_unit_path: str | None = None,
        max_results: int | None = None,
    ) -> [datamodels.OrgUnit]:
        """ List organizational units for a given customer.

        Args:
            customer_id (str): Unique google workspace account customer id.
            org_unit_path (str | None): The full path of an organization unit.
            All users in the organization will be returned.
            max_results (int | None): Maximum number of results to return.

        Returns:
            [datamodels.OrgUnit]: List of OrgUnits.
        """
        params: dict[str, str] = {"type": "ALL_INCLUDING_PARENT"}
        if org_unit_path is not None:
            params["orgUnitPath"] = org_unit_path

        request_url = self._get_full_url("list-ou", customer_id=customer_id)
        response = self.session.get(request_url, params=params)
        self.validate_response(
            response, f"Unable to list OU for customer id: {customer_id}"
        )
        if max_results is not None:
            return self.parser.build_org_units_objs(response.json())[:max_results]

        return self.parser.build_org_units_objs(response.json())

    def delete_ou(self, customer_id: str, path: str):
        """
        Delete an OU (Organization Unit) in GSuite
        :param path: {str} The full path to the organizational unit.
        :param customer_id: {str} The unique ID for the customer's G Suite
            account. As an account administrator, you can also use the
            my_customer alias to represent your account's customerId.
        :return: raise Exception if failed to validate response.
        """
        request_url = self._get_full_url(
            "delete-ou", customer_id=customer_id, org_path=path
        )
        response = self.session.delete(request_url)
        self.validate_response(
            response,
            f"Unable to delete OU for customer id {customer_id} \
            with organization path {path}",
        )

    def delete_group(self, group_email_address: str):
        """
        Delete a Group in GSuite
        :param customer_id: {str} The unique ID for the customer's G Suite
            account. As an account administrator, you can also use the
            my_customer alias to represent your account's customerId.
        :param group_email_address: {str} the unique email address of the group to be deleted
        :return:
            raise GSuiteNotFoundException exception if entity was not found in GSuite
            raise GSuiteValidationException exception if failed to validate request
        """
        request_url = self._get_full_url(
            "delete-group", group_email=group_email_address
        )
        response = self.session.delete(request_url)
        self.validate_response(
            response, error_msg=f"Failed to delete group {group_email_address}"
        )

    def list_role_assignments(
        self,
        customer_id: str,
        email: str,
        indirect_roles: bool = False,
        max_results: Optional[int] = None,
    ) -> [datamodels.RoleAssignment]:
        """
        List role assignments for a given customer.

        Args:
            customer_id (str): Unique google workspace account identificator.
            email (str): User email that the permissions will be checked for.
            indirect_roles (bool): Flag that enables the indirect roles are also listed.
            max_results (int): Maximum number of results to return.
        Returns:
            list[datamodels.RoleAssignment]: list of RoleAssignments
        """

        request_url = self._get_full_url(
            "list-role-assignments", customer_id=customer_id
        )
        params = {"userKey": email, "includeIndirectRoleAssignments": indirect_roles}
        raw_role_assignements = self._paginate_results(
            method="GET",
            url=request_url,
            params=params,
            results_key="items",
            limit=max_results,
            error_msg="Unable to paginate list role assignments results",
        )
        return [
            self.parser.build_role_assignment_obj(assignment)
            for assignment in raw_role_assignements
        ]

    def get_role(self, customer_id: str, role_id: str) -> datamodels.Role:
        """
        Get role details based on the role ID.

        Args:
            customer_id (str): Unique google workspace account identificator.
            role_id (str): ID of the role you want to get the details for.

        Returns:
            datamodels.Role: Details of a Role.
        """
        request_url = self._get_full_url(
            "get-role", customer_id=customer_id, role_id=role_id
        )
        response = self.session.get(request_url)
        self.validate_response(
            response, error_msg=f"Failed to get role details for {role_id}"
        )
        return self.parser.build_role_obj(response.json())

    def get_group(self, group_id: str) -> datamodels.Group:
        """
        Get group details based on the group ID.

        Args:
            group_id (str): ID of the group you want to get the details for.

        Returns:
            datamodels.Group Details of a Group.
        """
        request_url = self._get_full_url("get-group", group_id=group_id)
        response = self.session.get(request_url)
        self.validate_response(
            response, error_msg=f"Failed to get role details for {group_id}"
        )
        return self.parser.build_group_obj(response.json())

    def get_group_settings(self, group_id: str) -> datamodels.GroupsSettings:
        """
        Get gruop settings based on the indentifier.

        Args:
            group_id (str): The group's email address.

        Returns:
            datamodels.GroupsSettings Settings of a Group.
        """
        request_url = self._get_full_url("list-group-permissions", group_id=group_id)
        response = self.session.get(request_url)
        self.validate_response(
            response, error_msg=f"Failed to get group settings for {group_id}"
        )
        return self.parser.build_group_settings_obj(response.json())

    def _filter_emails(
        self,
        email_addresses: Optional[list],
        base_query: str,
        base_params: dict,
        custom_query: Optional[str],
        request_url: str,
        limit: Optional[int],
    ):
        if email_addresses:
            users_results = []
            for email in email_addresses:
                email_query = f"{base_query} {self._query_builder(email=email)}"
                params = {
                    **base_params,
                    "query": (
                        f"{email_query} {custom_query}" if custom_query else email_query
                    ),
                }
                raw_users_results = self._paginate_results(
                    method="GET",
                    url=request_url,
                    results_key="users",
                    params=utils.remove_empty_kwargs(**params),
                    limit=limit,
                    error_msg="Unable to paginate list users results",
                )
                users_results.extend(raw_users_results)
            return users_results
        params = {
            **base_params,
            "query": f"{base_query} {custom_query}" if custom_query else base_query,
        }
        return self._paginate_results(
            method="GET",
            url=request_url,
            results_key="users",
            params=utils.remove_empty_kwargs(**params),
            limit=limit,
            error_msg="Unable to paginate list users results",
        )

    def _paginate_results(
        self,
        method: str,
        url: str,
        results_key: str,
        params: SingleJson | None = None,
        body: SingleJson | None = None,
        limit: int | None = None,
        limit_param_name: str = "maxResults",
        error_msg: str = "Unable to paginate results",
    ) -> list:
        """Paginate results from the G Suite API.

        Args:
            method (str): The HTTP method for the request (e.g., 'GET', 'POST').
            url (str): The API endpoint URL.
            results_key (str): The key in the JSON response that contains the list of
                results.
            params (SingleJson | None): A dictionary of query parameters for the
                request. Defaults to None.
            body (SingleJson | None): A dictionary for the request body (for
                POST/PUT requests). Defaults to None.
            limit (int | None): The maximum number of results to return. Defaults
                to None (no limit).
            limit_param_name (str): The name of the parameter used for limiting
                results (e.g., 'maxResults').
            error_msg (str): The error message to use if a request fails.

        Returns:
            list: A list of all fetched results.
        """
        if params is None:
            params = {}
        if limit is not None:
            params.update({limit_param_name: limit})

        response: requests.Response = self.session.request(
            method=method, url=url, params=params, json=body
        )
        self.validate_response(response, error_msg)
        results: list[SingleJson] = response.json().get(results_key, [])

        while response.json().get("nextPageToken"):
            if limit and len(results) >= limit:
                break
            params.update({"pageToken": response.json()["nextPageToken"]})
            response: requests.Response = self.session.request(
                method=method, url=url, params=params, json=body
            )
            self.validate_response(response, error_msg)
            results.extend(response.json().get(results_key, []))

        return results[:limit] if limit else results

    @staticmethod
    def validate_response(response, error_msg="An error occurred"):
        """
        Validate GSuite response
        :param response: {json/html} response from GSuite api
        :param error_msg: {str} error message to display
        :return:
            raise GSuiteManagerError exception if failed to validate response's status code
            raise GSuiteEntityExistsException exception if entity already exists in GSuite
            raise GSuiteNotFoundException exception if entity was not found in GSuite
            raise GSuiteValidationException exception if failed to validate request
        """
        try:
            if response.status_code == consts.API_CONFLICT_STATUS_CODE:
                raise GSuiteEntityExistsException(
                    f"{error_msg}: {response.json().get('error', {}).get('message')}"
                )
            if response.status_code == consts.API_NOT_FOUND_STATUS_CODE:
                raise GSuiteNotFoundException(
                    f"{error_msg}: {response.json().get('error', {}).get('message')}"
                )
            if response.status_code == consts.API_BAD_REQUEST_STATUS_CODE:
                raise GSuiteValidationException(
                    f"{error_msg}: {response.json().get('error', {}).get('message')}"
                )
            response.raise_for_status()
        except requests.HTTPError as error:
            try:
                response.json()
            except json.JSONDecodeError as err:
                # Not a JSON - return content
                error_message = f"{error_msg}: {error.response.content}"
                raise GSuiteManagerError(error_message) from err
            raise GSuiteManagerError(
                f"{error_msg}: {response.json().get('error', {}).get('message')}"
            )

    def list_user_activity_events(
        self,
        user_key: str,
        application_name: str,
        start_time: str,
        end_time: str,
        limit: int,
    ) -> list[datamodels.UserActivityEvent]:
        """
        Return information about the activities performed by the user in a specific
        application.

        Args:
            user_key (str): The user's primary email address, alias email address, or
            unique user ID.
            application_name (str): The name of the application to fetch events for.
            start_time (str): The start time for the results in ISO 8601 format.
            end_time (str): The end time for the results in ISO 8601 format.
            limit (int): The maximum number of events to return from the API for this
            application.

        Returns:
            list[datamodels.UserActivityEvent]: A list of found event datamodels.
        """
        request_url: str = self._get_full_url(
            "list-user-activity",
            user_key=user_key,
            application_name=application_name,
        )
        params: dict[str, str] = {
            "startTime": start_time,
            "endTime": end_time,
        }

        try:
            raw_events: list[SingleJson] = self._paginate_results(
                method="GET",
                url=request_url,
                params=params,
                results_key="items",
                limit=limit,
                error_msg=(
                    f"Unable to list activity events for user {user_key} in application"
                    f" {application_name}"
                ),
            )
            return [
                self.parser.build_user_activity_event_obj(event) for event in raw_events
            ]
        except GSuiteNotFoundException as e:
            self.logger.info(
                f"No activity logs found for user '{user_key}' in application "
                f"'{application_name}'. This could mean the user does not exist or has "
                f"no activity. Error: {e}"
            )
            return []
        except GSuiteManagerError as e:
            self.logger.error(
                f"An error occurred while fetching activity events for user {user_key}:"
                f" {e}"
            )
            raise

    def get_host_browser_details(self, hostname: str) -> list[datamodels.Browser]:
        """
        Get browser details associated with a given hostname.

        Args:
            hostname (str): The hostname to search for.

        Returns:
            list[datamodels.Browser]: A list of Browser objects.
        """
        endpoint: str = self._get_full_url(
            "list_host_browsers", customer_id=consts.CUSTOMER
        )
        params: dict[str, str] = {
            "query": f"machine_name:{hostname}",
            "orderBy": "machine_name",
            "sortOrder": "ASCENDING",
            "projection": "FULL",
        }

        browsers_data: list[dict] = self._paginate_results(
            method="GET",
            url=endpoint,
            params=params,
            results_key="browsers",
            limit=100,
            error_msg=f"Failed to get browser details for host {hostname}",
        )

        return [self.parser.build_browser_obj(raw_data) for raw_data in browsers_data]

    def get_extension_details(
        self,
        extension_id: str,
        customer_id: str = consts.CUSTOMER,
    ) -> datamodels.ExtensionDetails:
        """
        Get information about a Chrome extension.
        Args:
            extension_id (str): The ID of the extension.
            customer_id (str): The customer ID. Defaults to "my_customer".

        Returns:
            datamodels.ExtensionDetails: The details of the extension.
        """
        request_url: str = self._get_full_url(
            "get-extension-details",
            base_url=consts.CHROME_API_ROOT,
            customer_id=customer_id,
            extension_id=extension_id,
        )
        response: requests.Response = self.session.get(request_url)
        self.validate_response(
            response, error_msg=f"Failed to get details for extension {extension_id}"
        )
        return self.parser.build_extension_details_obj(response.json())

    def get_extension_requesting_users(
        self,
        extension_id: str,
        page_size: int,
        customer_id: str = consts.CUSTOMER,
        org_unit_id: str | None = None,
    ) -> list[datamodels.RequestingUser]:
        """
        Get a list of users that requested an extension to be installed.
        Args:
            extension_id (str): The ID of the extension.
            page_size (int): The number of results to return.
            customer_id (str): The customer ID. Defaults to "my_customer".
            org_unit_id (str, optional): The ID of the organizational unit. Defaults
            to None.

        Returns:
            list[datamodels.RequestingUser]: A list of users.
        """
        request_url: str = self._get_full_url(
            "get-extension-users",
            base_url=consts.CHROME_API_ROOT,
            customer_id=customer_id,
        )
        params: dict[str, str | None] = {
            "extensionId": extension_id,
            "orgUnitId": org_unit_id,
        }

        raw_users: list[dict] = self._paginate_results(
            method="GET",
            url=request_url,
            params=utils.remove_empty_kwargs(**params),
            results_key="userDetails",
            limit=page_size,
            limit_param_name="pageSize",
            error_msg=f"Unable to fetch users requesting extension {extension_id}",
        )

        return [self.parser.build_requesting_user_obj(user) for user in raw_users]

    def get_extension_requesting_devices(
        self,
        extension_id: str,
        page_size: int,
        customer_id: str = consts.CUSTOMER,
        org_unit_id: str | None = None,
    ) -> list[datamodels.RequestingDevice]:
        """
        Get a list of devices that requested an extension to be installed.
        Args:
            extension_id (str): The ID of the extension.
            page_size (int): The number of results to return.
            customer_id (str): The customer ID. Defaults to "my_customer".
            org_unit_id (str, optional): The ID of the organizational unit. Defaults
            to None.

        Returns:
            list[datamodels.RequestingDevice]: A list of devices.
        """
        request_url: str = self._get_full_url(
            "get-extension-devices",
            base_url=consts.CHROME_API_ROOT,
            customer_id=customer_id,
        )
        params: dict[str, str | None] = {
            "extensionId": extension_id,
            "orgUnitId": org_unit_id,
        }

        raw_devices: list[dict] = self._paginate_results(
            method="GET",
            url=request_url,
            params=utils.remove_empty_kwargs(**params),
            results_key="deviceDetails",
            limit=page_size,
            limit_param_name="pageSize",
            error_msg=f"Unable to fetch devices requesting extension {extension_id}",
        )

        return [
            self.parser.build_requesting_device_obj(device) for device in raw_devices
        ]

    def block_extension(
        self,
        extension_id: str,
        org_unit_id: str,
        customer_id: str = consts.CUSTOMER,
    ) -> None:
        """
        Block a Chrome extension for a given organizational unit.
        Args:
            extension_id (str): The ID of the extension to block.
            org_unit_id (str): The ID of the organizational unit.
            customer_id (str): The customer ID. Defaults to "my_customer".
        """
        request_url: str = self._get_full_url(
            "batch-modify-policy",
            base_url=consts.CHROME_POLICY_API_ROOT,
            customer_id=customer_id,
        )

        payload: SingleJson = {
            "requests": [
                {
                    "policyTargetKey": {
                        "targetResource": f"orgunits/{org_unit_id}",
                        "additionalTargetKeys": {"app_id": f"chrome:{extension_id}"},
                    },
                    "policyValue": {
                        "policySchema": "chrome.users.apps.InstallType",
                        "value": {"appInstallType": "BLOCKED"},
                    },
                    "updateMask": {"paths": "appInstallType"},
                }
            ]
        }

        response: requests.Response = self.session.post(request_url, json=payload)
        self.validate_response(
            response,
            error_msg=f"Failed to block extension {extension_id} for OU {org_unit_id}",
        )

    def resolve_policy(
        self,
        extension_id: str,
        org_unit_id: str,
        customer_id: str = consts.CUSTOMER,
    ) -> list[datamodels.ResolvedPolicy]:
        """
        Resolves the effective policy for a given target.
        Args:
            extension_id (str): The ID of the extension.
            org_unit_id (str): The ID of the organizational unit.
            customer_id (str): The customer ID. Defaults to "my_customer".
        Returns:
            list[datamodels.ResolvedPolicy]: A list of resolved policy objects.
        """
        request_url: str = self._get_full_url(
            "resolve-policy",
            base_url=consts.CHROME_POLICY_API_ROOT,
            customer_id=customer_id,
        )

        payload: SingleJson = {
            "policyTargetKey": {
                "targetResource": f"orgunits/{org_unit_id}",
                "additionalTargetKeys": {"app_id": f"chrome:{extension_id}"},
            },
            "policySchemaFilter": "chrome.users.apps.InstallType",
        }

        response: requests.Response = self.session.post(request_url, json=payload)
        self.validate_response(
            response,
            error_msg=(
                f"Failed to resolve policy for extension {extension_id} for "
                f"OU {org_unit_id}"
            ),
        )
        return self.parser.build_resolved_policies_objs(response.json())

    def delete_extension_policy(
        self,
        extension_id: str,
        org_unit_id: str,
        customer_id: str = consts.CUSTOMER,
    ) -> None:
        """
        Delete a Chrome extension policy for a given organizational unit by
        reverting it to the inherited policy.

        Args:
            extension_id (str): The ID of the extension policy to delete.
            org_unit_id (str): The ID of the organizational unit.
            customer_id (str): The customer ID. Defaults to "my_customer".
        """
        request_url: str = self._get_full_url(
            "batch-inherit-policy",
            base_url=consts.CHROME_POLICY_API_ROOT,
            customer_id=customer_id,
        )

        payload: SingleJson = {
            "requests": [
                {
                    "policyTargetKey": {
                        "targetResource": f"orgunits/{org_unit_id}",
                        "additionalTargetKeys": {
                            "app_id": f"chrome:{extension_id}"
                        },
                    },
                    "policySchema": "chrome.users.apps.*",
                }
            ]
        }

        response: requests.Response = self.session.post(request_url, json=payload)
        self.validate_response(
            response,
            error_msg=(
                f"Failed to delete extension policy {extension_id} for OU {org_unit_id}"
            ),
        )

    def remove_extension_policy(
        self,
        extension_id: str,
        org_unit_id: str,
        customer_id: str = consts.CUSTOMER,
    ) -> None:
        """
        Remove a Chrome extension policy for a given organizational unit.
        Difference from delete_extension_policy lays in actual deletion of extension
        within Chrome browser instead of marking it as disabled.

        Args:
            extension_id (str): The ID of the extension policy to delete.
            org_unit_id (str): The ID of the organizational unit.
            customer_id (str): The customer ID. Defaults to "my_customer".
        """
        request_url: str = self._get_full_url(
            "batch-modify-policy",
            base_url=consts.CHROME_POLICY_API_ROOT,
            customer_id=customer_id,
        )

        payload: SingleJson = {
            "requests": [
                {
                    "policyTargetKey": {
                        "targetResource": f"orgunits/{org_unit_id}",
                        "additionalTargetKeys": {"app_id": f"chrome:{extension_id}"},
                    },
                    "policyValue": {
                        "policySchema": "chrome.users.apps.InstallType",
                        "value": {"appInstallType": "REMOVE"},
                    },
                    "updateMask": {"paths": "appInstallType"},
                }
            ]
        }

        response: requests.Response = self.session.post(request_url, json=payload)

        self.validate_response(
            response,
            error_msg=f"Failed to remove extension {extension_id} for OU {org_unit_id}",
        )
