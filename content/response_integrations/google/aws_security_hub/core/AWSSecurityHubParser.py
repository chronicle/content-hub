from __future__ import annotations
from . import consts
from .datamodels import Finding, InsightResults, ProcessedFinding, UnprocessedFinding


class AWSSecurityHubParser:
    """
    AWS Security Hub Transformation Layer.
    """

    @staticmethod
    def build_siemplify_finding_obj(raw_data):
        """
        :param raw_data: raw json response of single element in 'Findings' raw data response
        :return: Finding data model.
        """
        return Finding(
            raw_data,
            created_at=raw_data.get("CreatedAt"),
            updated_at=raw_data.get("UpdatedAt"),
            first_observed_at=raw_data.get("FirstObservedAt"),
            last_observed_at=raw_data.get("LastObservedAt"),
            description=raw_data.get("Description"),
            finding_id=raw_data.get("Id"),
            product_arn=raw_data.get("ProductArn"),
            title=raw_data.get("Title"),
            severity_label=raw_data.get("Severity", {}).get("Label"),
            generator_id=raw_data.get("GeneratorId"),
            compliance_status=raw_data.get("Compliance", {}).get("Status"),
        )

    @staticmethod
    def build_insight_results(raw_data, max_results=consts.DEFAULT_NUM_INSIGHT_DETAILS):
        """
        :param raw_data: {dict} dict of 'InsightResults' key of raw data response
        :param max_results: {int} max insight results to process. Must be a non-negative value.
        :return: InsightResults data model. Return values of the insight will be limited to max_results parameter
        """
        raw_result_values = raw_data.get("ResultValues")
        result_values_datamodels = []
        if raw_result_values:
            for raw_result in raw_result_values[:max_results]:
                result_values_datamodels.append(
                    InsightResults.ResultValue(
                        group_attribute_value=raw_result.get("GroupByAttributeValue"),
                        count=raw_result.get("Count"),
                    )
                )

        return InsightResults(
            raw_data,
            insight_arn=raw_data.get("InsightArn"),
            group_by_attribute=raw_data.get("GroupByAttribute"),
            result_values=result_values_datamodels,
        )

    @staticmethod
    def build_processed_finding(raw_data):
        """
        :param raw_data: {list} of single processed finding from json of 'ProcessedFindings' list of raw data response
        :return: ProcessedFinding data model if raw_data is not None or empty. otherwise return None
        """
        if raw_data:
            raw_data = raw_data[0]  # take first finding in list
            return ProcessedFinding(
                finding_id=raw_data.get("Id"), product_arn=raw_data.get("ProductArn")
            )
        return None

    @staticmethod
    def build_unprocessed_finding(raw_data):
        """
        :param raw_data: {list} of single unprocessed finding from json of 'UnprocessedFindings' list of raw data response
        :return: UnprocessedFinding data model if raw_data is not None or empty. otherwise return None
        """
        if raw_data:
            raw_data = raw_data[0]  # take first finding in list
            return UnprocessedFinding(
                finding_id=raw_data.get("FindingIdentifier", {}).get("Id"),
                product_arn=raw_data.get("FindingIdentifier", {}).get("ProductArn"),
                error_code=raw_data.get("ErrorCode"),
                error_message=raw_data.get("ErrorMessage"),
            )
        return None
