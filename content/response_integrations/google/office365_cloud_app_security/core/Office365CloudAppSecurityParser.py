from __future__ import annotations
from .datamodels import (
    Alert,
    Activity,
    SiemplifyPriorityEnum,
    CloudAppPriorityEnum,
    Entity,
    File,
    IpAddressRange,
)
from soar_sdk.SiemplifyUtils import convert_unixtime_to_datetime
from .constants import CONTAINS, FILTER_KEY_RESPONSE_KEY_MAPPING

DEFAULT_ALERT_NAME = "No alert name found"
DEFAULT_RULE_GENERATOR_NAME = "No rule generator found"
DEFAULT_PRODUCT = "Office 365 Cloud App Security"
POLICY_RULE_TYPE = "policyRule"
SERVICE_TYPE = "service"


class Office365CloudAppSecurityParser:
    def __init__(self, siemplify_logger=None):
        self.siemplify_logger = siemplify_logger

    @staticmethod
    def extract_rule_generator(alert_data):
        for entity in alert_data.get("entities", []):
            if entity.get("type") == POLICY_RULE_TYPE:
                return entity.get("label")

        return DEFAULT_RULE_GENERATOR_NAME

    @staticmethod
    def extract_product(alert_data):
        for entity in alert_data.get("entities", []):
            if entity.get("type") == SERVICE_TYPE:
                return entity.get("label")

        return DEFAULT_PRODUCT

    def build_siemplify_alert_obj(self, alert_data):
        return Alert(
            raw_data=alert_data,
            alert_name=alert_data.get("title", DEFAULT_ALERT_NAME),
            rule_generator=self.extract_rule_generator(alert_data),
            alert_id=alert_data.get("_id"),
            alert_severity=self.calculate_priority(alert_data.get("severityValue")),
            start_time=alert_data.get("timestamp", 1),
            end_time=alert_data.get("timestamp", 1),
            product_name=self.extract_product(alert_data),
            vendor_name=self.extract_product(alert_data),
            description=alert_data.get("description"),
        )

    def build_siemplify_activity_obj(self, activity_data):
        return Activity(
            raw_data=activity_data,
            description=self.extract_description(activity_data),
            user=self.extract_user(activity_data),
            ip_address=self.extract_ip(activity_data),
            location=self.extract_address(activity_data),
            device=self.extract_device(activity_data),
            date=self.extract_time(activity_data),
        )

    @staticmethod
    def calculate_priority(alert_severity):
        """
        The function calculates case priority by the Priority Map.
        :param alert_severity: severity value as it came from Cloud App {string}
        :return: calculated Siemplify alarm priority {integer}
        """
        # Low.
        if alert_severity == CloudAppPriorityEnum.LOW.value:
            return SiemplifyPriorityEnum.LOW.value
        # Medium
        elif alert_severity == CloudAppPriorityEnum.MEDIUM.value:
            return SiemplifyPriorityEnum.MEDIUM.value
        # High
        elif alert_severity == CloudAppPriorityEnum.HIGH.value:
            return SiemplifyPriorityEnum.HIGH.value

        # Informative
        return SiemplifyPriorityEnum.INFO.value

    @staticmethod
    def extract_description(activity):
        return activity.get("description", "")

    @staticmethod
    def extract_user(activity):
        return " ".join(
            data.get("id", {}).get("id", "") if data else ""
            for data in (
                list(activity.get("entityData", {}).values())
                if activity.get("entityData", {})
                else []
            )
        )

    @staticmethod
    def extract_ip(activity):
        return " ".join(activity.get("internals", {}).get("otherIPs", ""))

    @staticmethod
    def extract_address(activity):
        return " ".join(
            [
                activity.get("location", {}).get("city", ""),
                activity.get("location", {}).get("countryCode", ""),
            ]
        )

    @staticmethod
    def extract_device(activity):
        return f"{activity.get('userAgent', {}).get('name', '')} {activity.get('userAgent', {}).get('deviceType', '')} {activity.get('userAgent', {}).get('operatingSystem', {}).get('name', '')}"

    @staticmethod
    def extract_time(activity):
        return str(convert_unixtime_to_datetime(int(activity.get("timestamp", 0))))

    @staticmethod
    def build_siemplify_entity_obj(raw_entity: dict):
        return Entity(
            raw_data=raw_entity,
            is_admin=raw_entity.get("isAdmin"),
            is_external=raw_entity.get("isExternal"),
            role=raw_entity.get("role"),
            email=raw_entity.get("email"),
            domain=raw_entity.get("domain"),
            threat_score=raw_entity.get("threatScore"),
            is_fake=raw_entity.get("isFake"),
        )

    def build_files_obj_list(
        self,
        raw_data,
        filter_key=None,
        filter_logic=None,
        filter_value=None,
        limit=None,
    ):
        """
        Function that builds a list of objects
        :param raw_data: {string} Raw response
        :param filter_key: {string} What key should be used in the filter
        :param filter_value: {string} What value should be used in the filter
        :param filter_logic: {string} What filter logic should be applied.
        :param limit: {string} Limit for returned data
        :return {List} List of File objects
        """
        filtered_data = []

        for item in raw_data:
            if filter_value and filter_logic == CONTAINS:
                if (
                    str(filter_value).lower()
                    in str(
                        item.get(
                            FILTER_KEY_RESPONSE_KEY_MAPPING.get(filter_key, ""), ""
                        )
                    ).lower()
                ):
                    filtered_data.append(self.build_siemplify_file_obj(item))
            else:
                filtered_data.append(self.build_siemplify_file_obj(item))

        return filtered_data[:limit] if limit else filtered_data

    @staticmethod
    def build_siemplify_file_obj(raw_data):
        return File(
            raw_data=raw_data,
            name=raw_data.get("name"),
            owner_name=raw_data.get("ownerName"),
            owner_address=raw_data.get("ownerAddress"),
            alternate_link=raw_data.get("alternateLink"),
            app_name=raw_data.get("appName"),
            is_folder=raw_data.get("isFolder"),
            created_date=raw_data.get("createdDate"),
            modified_date=raw_data.get("modifiedDate"),
        )

    @staticmethod
    def build_ip_address_range_object(raw_data):
        return IpAddressRange(
            raw_data=raw_data,
            id=raw_data.get("_id"),
            name=raw_data.get("name"),
            subnets=[
                subnet.get("originalString") for subnet in raw_data.get("subnets", [])
            ],
            category=raw_data.get("category"),
            organization=raw_data.get("organization"),
            tags=[tag.get("name") for tag in raw_data.get("tags", [])],
        )
