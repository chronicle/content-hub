# ============================================================================#
# title           :ActiveDirectoryParser.py
# description     :This Module contains the Parsers from the raw data based on the datamodel
# author          :aniazyan@siemplify.co
# date            :18-12-2019
# python_version  :2.7
# libraries       :
# requirements    :
# product_version :
# ============================================================================#


# ============================= IMPORTS ===================================== #

from __future__ import annotations
from .datamodels import User, Host, GroupMember


# ============================= CLASSES ===================================== #
class ActiveDirectoryParserError(Exception):
    """
    General Exception for ActiveDirectory DataModel Parser
    """

    pass


class ActiveDirectoryParser:
    def __init__(self, siemplify_logger=None):
        self.siemplify_logger = siemplify_logger

    def build_siemplify_user_object(self, user_data, groups=[]):
        """
        Function that builds the user object based from the raw response
        :param user_data: {str} Raw User Data
        :param groups: {list} List of groups to attach the user
        :return {User} User object
        """
        telephone_num = user_data.get("telephoneNumber", [])
        name = user_data.get("name", [])
        return User(
            raw_data=user_data,
            name=name[0] if name else None,
            telephone_num=telephone_num[0] if telephone_num else None,
            manager=user_data.get("manager"),
            groups=groups,
        )

    def build_siemplify_host_object(self, host_data):
        """
        Function that builds the user object based from the raw response
        :param host_data: {str} Raw User Data
        :return {Host} Host object
        """
        return Host(raw_data=host_data)

    def build_siemplify_group_members(self, raw_data):
        return [
            self.build_siemplify_group_member_object(member_data)
            for member_data in raw_data
        ]

    def build_siemplify_group_member_object(self, member_data):
        """
        Function that builds the user object based from the raw response
        :param member_data: {str} Raw User Data
        :return {GroupMember} Instance of GroupMember class
        """
        return GroupMember(
            raw_data=member_data,
            cn=self._get_attribute(member_data.get("cn")),
            display_name=self._get_attribute(member_data.get("displayName")),
            distinguished_name=self._get_attribute(
                member_data.get("distinguishedName")
            ),
        )

    def get_user_groups(self, user_data):
        """
        Function that returns user's groups
        :return {list} list object containing user's group
        """
        groups = []
        for group in user_data.get("memberOf", []):
            # Extract group name from group dn
            try:
                groups.append(group.split(",")[0].split("=")[1])
            except IndexError as e:
                self.siemplify_logger.info(f"An IndexError occurred on group {group}")

        return groups

    @staticmethod
    def _get_attribute(attr):
        return attr[0] if attr else None
