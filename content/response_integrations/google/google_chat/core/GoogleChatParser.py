from __future__ import annotations
from .datamodels import *
from .constants import EQUAL


class GoogleChatParser:
    def build_spaces_obj_list(
        self,
        raw_data,
        filter_key=None,
        filter_logic=None,
        filter_value=None,
        limit=None,
    ):
        """
        Function that builds a list of spaces
        :param raw_data: {string} Raw response
        :param filter_key: {string} What key should be used in the filter
        :param filter_value: {string} What value should be used in the filter
        :param filter_logic: {string} What filter logic should be applied.
        :param limit: {string} Limit for returned data
        :return {List} List of users
        """
        spaces = raw_data.get("spaces")
        filtered_data = []

        for space in spaces:
            if filter_value:
                if filter_logic == EQUAL:
                    if space.get(filter_key, "") == filter_value:
                        filtered_data.append(self.build_spaces_obj(space))
                else:
                    if filter_value in space.get(filter_key, ""):
                        filtered_data.append(self.build_spaces_obj(space))
            else:
                filtered_data.append(self.build_spaces_obj(space))

        return filtered_data[:limit]

    @staticmethod
    def build_spaces_obj(raw_data):
        return Spaces(raw_data=raw_data, **raw_data)

    def build_membership_obj_list(self, raw_data):
        return [
            self.build_member_obj(raw_json)
            for raw_json in raw_data.get("memberships", [])
        ]

    def build_member_obj(self, raw_data):
        return Member(
            raw_data,
            display_name=raw_data.get("member", {}).get("displayName"),
            **raw_data
        )

    @staticmethod
    def build_message_obj(raw_data):
        return Message(raw_data=raw_data)
