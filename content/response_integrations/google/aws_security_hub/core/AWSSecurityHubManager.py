# ============================================================================#
# title           :AWSSecurityHubManager.py
# description     :This Module contain all AWS Security Hub operations functionality
# author          :gabriel.munits@siemplify.co
# date            :30-09-2020
# python_version  :3.7
# libraries       :boto3
# requirements     :
# product_version :1.0
# ============================================================================#

# ============================= IMPORTS ===================================== #
from __future__ import annotations
import boto3
from soar_sdk.SiemplifyUtils import convert_unixtime_to_datetime
from . import consts
from . import datamodels
from .AWSSecurityHubParser import AWSSecurityHubParser
from .UtilsManager import remove_empty_kwargs
from .exceptions import (
    AWSSecurityHubStatusCodeException,
    AWSSecurityHubValidationException,
)


class AWSSecurityHubManager:
    """
    AWS Security Hub Manager
    """

    VALID_STATUS_CODES = (200,)

    def __init__(
        self, aws_access_key, aws_secret_key, aws_default_region, verify_ssl=False
    ):
        self.aws_access_key = aws_access_key
        self.aws_secret_key = aws_secret_key
        self.aws_default_region = aws_default_region

        session = boto3.session.Session()

        self.client = session.client(
            "securityhub",
            aws_access_key_id=aws_access_key,
            aws_secret_access_key=aws_secret_key,
            region_name=aws_default_region,
            verify=verify_ssl,
        )
        self.parser = AWSSecurityHubParser()

    @staticmethod
    def validate_response(response, error_msg="An error occurred"):
        """
        Validate client Security Hub response status code
        :param response: client Security Hub response
        :return: raise AWSSecurityHubStatusCodeException if status code is not 200
        """
        if (
            response.get("ResponseMetadata", {}).get("HTTPStatusCode")
            not in AWSSecurityHubManager.VALID_STATUS_CODES
        ):
            raise AWSSecurityHubStatusCodeException(
                f"{error_msg}. Response: {response}"
            )

    def test_connectivity(self):
        """
        Test connectivity with AWS Security Hub service by calling get_master_account method
        :return: true if successfully tested conncetivity
                raise botocore.exceptions.ClientError if connectivity failed
                raise AWSSecurityHubStatusCodeException if connectivity failed to validate status code
        """
        response = self.client.get_master_account()
        self.validate_response(
            response,
            error_msg="Failed to test connectivity with AWS Security Hub Service.",
        )
        return True

    def get_findings_page(
        self,
        severities=None,
        start_time=None,
        end_time=None,
        page_size=consts.PAGE_SIZE,
        search_after_token=None,
        asc=True,
        sort_by="LastObservedAt",
    ):
        """
        Get findings single page by various filters.
        :param severities: {list} list of severities to fetch. Possible values: Informational, Low, Medium, High, Critical
        :param start_time: {datetime.datetime} search for findings that were created after the given start time
        :param end_time: {int} unix time search for findings that were created before the given end time
        :param page_size: {int} page size
        :param asc: {bool} if true, the findings will be in ascending order, otherwise descending
        :param sort_by: {str} field name to sort the results by
        :param search_after_token: {str} token from where to start fetching next page
        :return: {tuple} ({str} next token, {list} of Finding data model) next token will be None if all findings in Security Hub fetched
                raise AWSSecurityHubStatusCodeException if failed to validate response status code
                raise AWSSecurityHubValidationException if failed to validate parameters
        """ ""

        if severities:  # validate severities
            for severity in severities:
                if severity.upper() not in datamodels.SEVERITIES:
                    raise AWSSecurityHubValidationException(
                        f"{severity} is invalid value for severity field. "
                        f"Valid values: {','.join(datamodels.SEVERITIES.keys())}"
                    )

        pagination_config = {
            # limit the API to return Max findings in page iteration. If more results exist NextToken will be returned
            "MaxItems": page_size,
            "PageSize": page_size,  # page size
        }

        if search_after_token:  # continue previous pagination
            pagination_config["StartingToken"] = search_after_token

        paginator = self.client.get_paginator("get_findings")

        page_iterator = paginator.paginate(
            Filters={
                "WorkflowStatus": [{"Value": "NEW", "Comparison": "EQUALS"}],
                "RecordState": [{"Value": "ACTIVE", "Comparison": "EQUALS"}],
                "SeverityLabel": [
                    {"Value": severity.upper(), "Comparison": "EQUALS"}
                    for severity in severities
                ],
                "LastObservedAt": [
                    {
                        "Start": start_time.strftime(consts.TIME_FORMAT),
                        "End": convert_unixtime_to_datetime(end_time).strftime(
                            consts.TIME_FORMAT
                        ),
                    }
                ],
            },
            SortCriteria=[{"Field": sort_by, "SortOrder": "asc" if asc else "desc"}],
            PaginationConfig=pagination_config,
        )

        parsed_findings = []  # list of Finding data models
        search_after_token = None

        for page in page_iterator:
            self.validate_response(page, error_msg="Failed to get findings page.")
            raw_findings = page.get("Findings", [])
            search_after_token = page.get("NextToken")
            for finding in raw_findings:
                parsed_findings.append(self.parser.build_siemplify_finding_obj(finding))
            break

        return search_after_token, parsed_findings

    def get_insight_results(
        self, insight_arn, max_results=consts.DEFAULT_NUM_INSIGHT_DETAILS
    ):
        """
        Get Insight details
        :param insight_arn: {str} insight amazon resource name
        :param max_results: {int} maximum number of Result Values. Default is 50
        :return: InsightResults data model
                raise AWSSecurityHubStatusCodeException if failed to validate get insight results response status code
        """
        raw_insight_results = self.client.get_insight_results(InsightArn=insight_arn)
        self.validate_response(
            raw_insight_results, error_msg="Failed to get insight results."
        )

        raw_results = raw_insight_results.get("InsightResults")
        return self.parser.build_insight_results(raw_results, max_results=max_results)

    def create_insight(self, insight_name, filter_json, group_by_attribute):
        """
        Creates new insight
        :param insight_name: {str} name of the insight
        :param filter_json:  {dict} of one or more attributes used to filter the findings included in the insight.
        :param group_by_attribute: {str} the attribute used to group the findings for the insight.
        :return: {str} insight arn
                raise AWSSecurityHubStatusCodeException if failed to validate create insight response status code
        """
        insight_response = self.client.create_insight(
            Name=insight_name, Filters=filter_json, GroupByAttribute=group_by_attribute
        )
        self.validate_response(insight_response, error_msg="Failed to create insight.")

        return insight_response.get("InsightArn")

    def update_insight(
        self, insight_arn, insight_name=None, filter_json=None, group_by_attribute=None
    ):
        """
        Update existing insight
        :param insight_arn: {str} the ARN of the insight you want to update
        :param insight_name: {str} the updated name of the insight
        :param filter_json: {dict} the updated filters that define this insight.
        :param group_by_attribute: {str} the updated GroupBy attribute that definse this insight.
        :return:
                raise AWSSecurityHubStatusCodeException if failed to validate update insight response status code
        """
        payload_kwargs = remove_empty_kwargs(
            InsightArn=insight_arn,
            Name=insight_name,
            Filters=filter_json,
            GroupByAttribute=group_by_attribute,
        )
        update_insight_response = self.client.update_insight(**payload_kwargs)
        self.validate_response(
            update_insight_response, error_msg="Failed to update insight."
        )

    def update_finding(
        self,
        finding_id,
        product_arn,
        note_text=None,
        note_author=None,
        severity=None,
        verification_state=None,
        confidence=None,
        criticality=None,
        types=None,
        workflow_status=None,
        custom_fields=None,
    ):
        """
        Update information about investigation into a finding
        :param finding_id: {str} the identifier of the finding that was specified by the finding provider
        :param product_arn: {str} the arn generated by Security Hub that uniquely identifies a product
                                  that generates findings
        :param note_text: {str} the updated note text
        :param note_author: {str} the principal that updated the note
        :param severity: {str} the severity value of the finding. Possible Values 'Informational', 'Low', 'Medium', 'High', 'Critical'
        :param verification_state: {str} indicates the veracity of a finding
        :param confidence: {int} the updated value of the finding confidence
        :param criticality: {int} the updated value of the level of importance assigned to the
                                  resource associated with the findings
        :param types: {list} one or more finding types in the format of namespace/category/classifier that classify a finding.
        :param workflow_status: {str} the status of the investigation into a finding. The allowed values are the
                                following: 'New', 'Notified', 'Resolved', 'Surpressed'
        :param custom_fields: {dict} custom user-defined name/value string pairs fields added to a finding
        :return: {tuple} processed_finding, unprocessed_finding - each is a ProcessedFinding and UnprocessedFinding data model respectively.
                         one of the values always will be None, because finding is either processed or not.
                raise AWSSecurityHubStatusCodeException if failed to validate update insight response status code
                raise AWSSecurityHubValidationException if failed to validate parameters
        """

        payload_kwargs = remove_empty_kwargs(
            FindingIdentifiers=[{"Id": finding_id, "ProductArn": product_arn}],
            # both note_text and note_author must not be None (or empty), otherwise None
            Note=(
                {"Text": note_text, "UpdatedBy": note_author}
                if (note_text and note_author)
                else None
            ),
            Severity={"Label": severity} if severity else None,
            VerificationState=verification_state if verification_state else None,
            Confidence=confidence if confidence is not None else None,
            Criticality=criticality if criticality is not None else None,
            Types=types if types else None,
            UserDefinedFields=custom_fields if custom_fields else None,
            Workflow={"Status": workflow_status} if workflow_status else None,
        )

        update_findings_response = self.client.batch_update_findings(**payload_kwargs)

        self.validate_response(
            update_findings_response, error_msg="Failed to update finding."
        )

        processed_finding = self.parser.build_processed_finding(
            update_findings_response.get("ProcessedFindings")
        )
        unprocessed_finding = self.parser.build_unprocessed_finding(
            update_findings_response.get("UnprocessedFindings")
        )

        return processed_finding, unprocessed_finding
