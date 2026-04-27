from __future__ import annotations
import uuid

from TIPCommon import dict_to_flat
from . import consts
from soar_sdk.SiemplifyConnectorsDataModel import AlertInfo
from soar_sdk.SiemplifyUtils import convert_string_to_unix_time

SEVERITIES = {  # map security hub finding severity to siemplify severity
    "INFORMATIONAL": -1,
    "LOW": 40,
    "MEDIUM": 60,
    "HIGH": 80,
    "CRITICAL": 100,
}


class Finding:
    """
    Security Hub Finding data model.
    """

    def __init__(
        self,
        raw_data,
        created_at=None,
        updated_at=None,
        first_observed_at=None,
        last_observed_at=None,
        description=None,
        finding_id=None,
        product_arn=None,
        title=None,
        severity_label=None,
        generator_id=None,
        compliance_status=None
    ):
        self.raw_data = raw_data
        self.created_time = (created_at,)
        self.updated_time = (updated_at,)

        self.description = description
        self.id = finding_id
        self.last_observed_at = last_observed_at
        self.product_arn = product_arn
        self.rule_name = title
        self.severity = severity_label
        self.siemplify_severity = SEVERITIES.get(severity_label, -1)
        self.rule_generator = generator_id
        self.status = compliance_status  # PASSED, WARNING, FAILED, NOT_AVAILABLE

        try:
            self.first_observed_time_ms = convert_string_to_unix_time(first_observed_at)
        except Exception:
            self.first_observed_time_ms = 1

        try:
            self.last_observed_time_ms = convert_string_to_unix_time(last_observed_at)
        except Exception:
            self.last_observed_time_ms = 1

    def as_json(self):
        return self.raw_data

    def as_event(self):
        """
        Return Finding data model as siemplify event
        :return: {dict} flatted raw json data
        """
        return dict_to_flat(self.raw_data)

    def as_flat(self):
        """
        Return finding's flatted raw data
        :return: {dict} flatted raw json data of the finding
        """
        return dict_to_flat(self.raw_data)

    def as_alert_info(self, environment_common, device_product_field):
        """
        Create an AlertInfo out of the current finding
        :param environment_common: {EnvironmentHandle} The environment common object for fetching the environment
        :param device_product_field: {str} Device product field name
        :return: {AlertInfo} The created AlertInfo object
        """
        alert_info = AlertInfo()
        alert_info.environment = environment_common.get_environment(self.as_event())
        alert_info.ticket_id = self.id
        alert_info.display_id = str(uuid.uuid4())
        alert_info.name = self.rule_name
        alert_info.description = self.description
        alert_info.device_vendor = consts.VENDOR
        alert_info.device_product = (
            self.as_flat().get(device_product_field) or consts.PRODUCT
        )
        alert_info.priority = self.siemplify_severity
        alert_info.rule_generator = self.rule_generator
        alert_info.start_time = self.first_observed_time_ms
        alert_info.end_time = self.last_observed_time_ms
        alert_info.events = [self.as_event()]  # alert <-> event
        return alert_info


class InsightResults:
    """
    Security Hub Insight result details data model.
    """

    class ResultValue:
        def __init__(self, group_attribute_value=None, count=None):
            self.group_attribute_value = group_attribute_value
            self.count = count

        def to_dict(self):
            """
            :return: {dict} of Insight Result data model as dictionary
            """
            return {
                "GroupByAttributeValue": self.group_attribute_value,
                "Count": self.count,
            }

        def as_csv(self):
            """
            :return: {dict} of Insight Result data model as csv representation
            """
            return {"Name": self.group_attribute_value, "Count": self.count}

    def __init__(
        self, raw_data, insight_arn=None, group_by_attribute=None, result_values=None
    ):
        """
        :param insight_arn: {str} insight aws resource name
        :param group_by_attribute: {str} insight group by attribute
        :param result_values: {list} of Result Value data models
        """
        self.raw_data = raw_data
        self.insight_arn = insight_arn
        self.group_by_attribute = group_by_attribute
        self.result_values = result_values

        pass

    def to_dict(self):
        """
        InsightResults data model to dictionary.
        :return: {dict} Insight Results as dictionary
        """
        return {
            "InsightArn": self.insight_arn,
            "GroupByAttribute": self.group_by_attribute,
            "ResultValues": [result.to_dict() for result in self.result_values],
        }

    def as_json(self):
        """
        InsightResults raw response
        :return: raw InsightResults response as json
        """
        return self.raw_data


class ProcessedFinding:
    """
    Processed Finding data model.
    """

    def __init__(self, finding_id, product_arn):
        self.finding_id = finding_id
        self.product_arn = product_arn


class UnprocessedFinding:
    """
    Unprocessed Finding data model.
    """

    def __init__(self, finding_id, product_arn, error_code, error_message):
        self.finding_id = finding_id
        self.product_arn = product_arn
        self.error_code = error_code
        self.error_message = error_message
