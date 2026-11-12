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
from .datamodels import User, Group, Host, Manager
from .exceptions import AzureADError
from .constants import GROUP_MEMBERS_FILTER_USER_DISPLAY_NAME, GROUP_MEMBERS_FILTER_USER_MAIL_NAME, GROUP_MEMBERS_FILTER_USER_PRINCIPAL_NAME


class AzureADParser:
    def build_results(
        self, raw_json, method, data_key="data", pure_data=False, limit=None, **kwargs
    ):
        return [
            getattr(self, method)(item_json, **kwargs)
            for item_json in (raw_json if pure_data else raw_json.get(data_key, []))[
                :limit
            ]
        ]

    @staticmethod
    def build_siemplify_user_object(user):
        return User(raw_data=user, **user)

    def get_host_values(self, raw_data):
        return self.build_results(
            raw_data.get("value", []), "build_siemplify_host_object", pure_data=True
        )

    @staticmethod
    def build_siemplify_host_object(raw_data):
        return Host(
            raw_data=raw_data,
            account_enabled=raw_data.get("accountEnabled"),
            name=raw_data.get("displayName"),
            id=raw_data.get("id"),
            operating_system=raw_data.get("operatingSystem"),
            os_version=raw_data.get("operatingSystemVersion"),
            profile_type=raw_data.get("profileType"),
            compliant=raw_data.get("isCompliant"),
            last_sign_in=raw_data.get("approximateLastSignInDateTime"),
        )

    @staticmethod
    def build_siemplify_group_object(group):
        """
        Function that builds the group object based from the raw response
        :param user: {string} Raw Group Data
        :return {Group} Group object
        """
        return Group(
            raw_data=group,
            name=group.get("displayName"),
            description=group.get("description"),
            id=group.get("id"),
            created_time=group.get("createdDateTime"),
            group_type=group.get("groupTypes"),
        )

    def build_siemplify_user_list(
        self, raw_data, filter_value=None, filter_logic=None, filter_key=None
    ):
        """
        Function that builds a list of users
        :param raw_data: {string} Raw response
        :param filter_value: {string} What value should be used in the filter
        :param filter_logic: {string} What filter logic should be applied.
        :return {List} List of users
        """
        users = raw_data.get("value")
        list_of_users = []
        for user in users:
            if filter_value:
                if filter_logic == "Equal":
                    if user.get("userPrincipalName", "") == filter_value:
                        list_of_users.append(self.build_siemplify_user_object(user))
                else:
                    if filter_value in user.get("userPrincipalName", ""):
                        list_of_users.append(self.build_siemplify_user_object(user))
            else:
                list_of_users.append(self.build_siemplify_user_object(user))
        return list_of_users

    def build_group_members_list(
        self, raw_data, filter_value=None, filter_logic=None, filter_key=None
    ):
        """
        Function that builds a list of users
        :param raw_data: {string} Raw response
        :param filter_value: {string} What value should be used in the filter
        :param filter_logic: {string} What filter logic should be applied.
        :param filter_key: {string} What key will be used for filtering
        :return {List} List of users
        """
        members = raw_data.get("value")
        list_of_members = []
        for member in members:
            if filter_value:
                if filter_logic == "Equal":
                    if filter_key == GROUP_MEMBERS_FILTER_USER_PRINCIPAL_NAME:
                        if member.get("userPrincipalName", "") == filter_value:
                            list_of_members.append(
                                self.build_siemplify_user_object(member)
                            )
                    if filter_key == GROUP_MEMBERS_FILTER_USER_DISPLAY_NAME:
                        if member.get("displayName", "") == filter_value:
                            list_of_members.append(
                                self.build_siemplify_user_object(member)
                            )
                    if filter_key == GROUP_MEMBERS_FILTER_USER_MAIL_NAME:
                        if member.get("mail", "") == filter_value:
                            list_of_members.append(
                                self.build_siemplify_user_object(member)
                            )

                elif filter_logic == "Contains":
                    if filter_key == GROUP_MEMBERS_FILTER_USER_PRINCIPAL_NAME:
                        if filter_value in member.get("userPrincipalName", ""):
                            list_of_members.append(
                                self.build_siemplify_user_object(member)
                            )
                    if filter_key == GROUP_MEMBERS_FILTER_USER_DISPLAY_NAME:
                        if filter_value in member.get("displayName", ""):
                            list_of_members.append(
                                self.build_siemplify_user_object(member)
                            )
                    if filter_key == GROUP_MEMBERS_FILTER_USER_MAIL_NAME:
                        member_mail = member.get("mail", "")
                        if member_mail is not None:
                            if filter_value in member_mail:
                                list_of_members.append(
                                    self.build_siemplify_user_object(member)
                                )

                else:
                    list_of_members.append(self.build_siemplify_user_object(member))
            else:
                list_of_members.append(self.build_siemplify_user_object(member))
        return list_of_members

    def build_siemplify_group_list(
        self, raw_data, filter_value=None, filter_logic=None, filter_key=None
    ):
        """
        Function that builds a list of group
        :param raw_data: {string} Raw response
        :param filter_value: {string} What value should be used in the filter
        :param filter_logic: {string} What filter logic should be applied.
        :return {List} List of groups
        """
        groups = raw_data.get("value")
        list_of_groups = []
        for group in groups:
            if filter_value:
                if filter_logic == "Equal":
                    if group.get("displayName", "") == filter_value:
                        list_of_groups.append(self.build_siemplify_group_object(group))
                else:
                    if filter_value in group.get("displayName", ""):
                        list_of_groups.append(self.build_siemplify_group_object(group))
            else:
                list_of_groups.append(self.build_siemplify_group_object(group))
        return list_of_groups

    @staticmethod
    def check_is_user_member_of(raw_data):
        return bool(raw_data.get("value"))

    @staticmethod
    def user_id_based_on_name(raw_data):
        if raw_data.get("id"):
            return raw_data["id"]

        raise AzureADError("Unable to get ID for the user")

    @staticmethod
    def build_users_manager_object(raw_data):
        temp_raw_data = raw_data.copy()
        mail_value = temp_raw_data.pop("mail", None)
        return Manager(
            raw_data=raw_data,
            context=raw_data.get("@odata.context"),
            mobile_phone=raw_data.get("mobilePhone"),
            name=raw_data.get("displayName"),
            mail=mail_value,
            **temp_raw_data
        )

    @staticmethod
    def build_user_registration_details(raw_data):
        """
        Build MFA registration details from raw data.
        :param raw_data: {dict} Raw response from API.
        :return: {dict} MFA registration details.
        """
        value = raw_data.get("value", [])
        return value[0] if value else {}

    def get_page_next_link(self, raw_data):
        return raw_data.get("@odata.nextLink", "")
