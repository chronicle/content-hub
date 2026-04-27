from __future__ import annotations
from .datamodels import *
from .constants import CONTAINS


class CloudflareParser:
    def build_results(self, raw_data, method, data_key="result", pure_data=False):
        items = (
            raw_data
            if pure_data
            else self.extract_data_from_raw_data(raw_data, data_key=data_key)
        )
        return [getattr(self, method)(item_json) for item_json in items]

    @staticmethod
    def extract_data_from_raw_data(raw_data, data_key="result"):
        return raw_data.get(data_key, [])

    @staticmethod
    def build_zone_object(raw_data):
        return Zone(raw_data=raw_data, zone_id=raw_data.get("id"))

    @staticmethod
    def build_firewall_rule_object(raw_data):
        return FirewallRule(
            raw_data=raw_data,
            id=raw_data.get("id"),
            description=raw_data.get("description"),
            action=raw_data.get("action"),
            filter=CloudflareParser.build_firewall_filter_object(
                raw_data.get("filter")
            ),
        )

    @staticmethod
    def build_firewall_filter_object(raw_data):
        return FirewallFilter(
            raw_data=raw_data,
            id=raw_data.get("id"),
            expression=raw_data.get("expression"),
        )

    @staticmethod
    def build_filtered_obj_list(
        obj_list, filter_key=None, filter_logic=None, filter_value=None, limit=None
    ):
        """
        Function that builds a list of filtered objects
        :param obj_list: {string} Raw response
        :param filter_key: {string} What key should be used in the filter
        :param filter_value: {string} What value should be used in the filter
        :param filter_logic: {string} What filter logic should be applied.
        :param limit: {string} Limit for returned data
        :return {List} List of objects
        """
        filtered_data = []

        for item in obj_list:
            if filter_value and filter_logic == CONTAINS:
                if str(filter_value).lower() in getattr(item, filter_key).lower():
                    filtered_data.append(item)
            else:
                filtered_data.append(item)

        return filtered_data[:limit] if limit else filtered_data

    @staticmethod
    def build_rule_list_object(raw_data):
        """
        Args:
            raw_data: Dict
        Returns:
            RuleList object
        """
        return RuleList(
            raw_data=raw_data,
            id=raw_data.get("id"),
            name=raw_data.get("name"),
            kind=raw_data.get("kind"),
            num_items=raw_data.get("num_items"),
            num_referencing_filters=raw_data.get("num_referencing_filters"),
            created_on=raw_data.get("created_on"),
            modified_on=raw_data.get("modified_on"),
        )

    @staticmethod
    def build_rule_list_item_object(raw_data):
        """
        Args:
            raw_data: Dict
        Returns:
            RuleListItem object
        """
        return RuleListItem(raw_data=raw_data)
