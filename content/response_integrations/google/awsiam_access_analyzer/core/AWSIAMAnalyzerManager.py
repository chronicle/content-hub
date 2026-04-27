# ============================================================================#
# title           :AWSIAMAnalyzerManager.py
# description     :This Module contain all AWS IAM Access Analyzer operations functionality
# author          :gabriel.munits@siemplify.co
# date            :24-11-2020
# python_version  :3.7
# libraries       :boto3
# requirements     :
# product_version :1.0
# ============================================================================#

from __future__ import annotations
from typing import Optional, List

# ============================= IMPORTS ===================================== #
import boto3
import botocore

from TIPCommon import filter_old_alerts
from . import consts
from .AWSIAMAnalyzerParser import AWSIAMAnalyzerParser
from .exceptions import (
    AWSIAMStatusCodeException,
    AWSIAMAnalyzerNotFoundException,
    AWSIAMNotFoundException,
)
from soar_sdk.SiemplifyUtils import convert_datetime_to_unix_time


class AWSIAMAnalyzerManager:
    """
    AWS IAM Analyzer Manager
    """

    VALID_STATUS_CODES = (200,)

    def __init__(
        self,
        aws_access_key,
        aws_secret_key,
        aws_default_region,
        analyzer_name,
        verify_ssl=False,
        siemplify=None,
    ):
        self.aws_access_key = aws_access_key
        self.aws_secret_key = aws_secret_key
        self.aws_default_region = aws_default_region
        self.analyzer_name = analyzer_name

        session = boto3.session.Session()

        self.client = session.client(
            "accessanalyzer",
            aws_access_key_id=aws_access_key,
            aws_secret_access_key=aws_secret_key,
            verify=verify_ssl,
            region_name=aws_default_region,
        )
        self.parser = AWSIAMAnalyzerParser()
        self.siemplify = siemplify

    @staticmethod
    def validate_response(response, error_msg="An error occurred"):
        """
        Validate client IAM Access Analyzer response status code
        :param response: client IAM Access Analyzer response
        :param error_msg: {str} error message to display if response failed validation
        :return: raise AWSIAMStatusCodeException if status code is not 200
        """
        if (
            response.get("ResponseMetadata", {}).get("HTTPStatusCode")
            not in AWSIAMAnalyzerManager.VALID_STATUS_CODES
        ):
            raise AWSIAMStatusCodeException(f"{error_msg}. Response: {response}")

    def test_connectivity(self):
        """
        Test connectivity with AWS Security Hub service by calling get_master_account method
        :return: true if successfully tested connectivity
                raise botocore.exceptions.ClientError if connectivity failed
                raise AWSIAMStatusCodeException if connectivity failed to validate status code
        """
        response = self.client.get_analyzer(analyzerName=self.analyzer_name)
        self.validate_response(
            response,
            error_msg="Failed to test connectivity with AWS IAM Analyzer Service.",
        )

    def get_analyzer(self):
        """
        Retrieves information about the specified analyzer.
        :return: {datamodels.Analyzer} analyzer data model.
                raise botocore.exceptions.ClientError if connectivity failed
                raise AWSIAMAnalyzerNotFoundException if analyzer not found
                raise AWSIAMStatusCodeException if connectivity failed to validate status code
        """
        try:
            response = self.client.get_analyzer(analyzerName=self.analyzer_name)
        except botocore.exceptions.ClientError as error:
            if (
                error.response.get("Error", {}).get("Code")
                == "ResourceNotFoundException"
            ):
                raise AWSIAMAnalyzerNotFoundException("Analyzer not found.")
            raise error

        self.validate_response(
            response, error_msg=f"Failed to get analyzer {self.analyzer_name}"
        )
        return self.parser.build_analyzer_obj(response)

    def update_findings(self, ids: list, analyzer_arn: str, status: str):
        """
        Update list of findings with a status
        :param ids: {list} list of finding ids
        :param analyzer_arn: {str} analyzer arn
        :param status: {str} the status to update the findings to. Can be 'ARCHIVED' or 'ACTIVE'
        :return:
                raise AWSIAMStatusCodeException if connectivity failed to validate status code
        """
        response = self.client.update_findings(
            analyzerArn=analyzer_arn, ids=ids, status=status
        )
        self.validate_response(
            response, error_msg=f"Failed to archive findings with id {', '.join(ids)}"
        )

    def archive_finding(self, ids: list, analyzer_arn: str):
        """
        Archive finding in AWS IAM Access Analyzer
        :param ids: {list} list of finding ids to archive
        :param analyzer_arn: {str} analyzer arn
        :return:
                raise AWSIAMStatusCodeException if connectivity failed to validate status code
        """
        return self.update_findings(ids, analyzer_arn, consts.ARCHIVED_STATUS)

    def start_resource_scan(self, resource_arn: str, analyzer_arn: str):
        """
        Start a scan of the policies applied to the specified resource
        :param resource_arn: {str} The ARN of the resource to scan.
        :param analyzer_arn: {str} The ARN of the analyzer to use to scan the policies applied to the specified resource.
        :return:
                raise AWSIAMStatusCodeException if connectivity failed to validate status code
                raise AWSIAMNotFoundException if analyzer was not found
        """
        response = self.client.start_resource_scan(
            analyzerArn=analyzer_arn, resourceArn=resource_arn
        )
        self.validate_response(
            response,
            error_msg=f"Failed to start resource scan for resource {resource_arn}",
        )

    def get_analyzed_resource(self, resource_arn: str, analyzer_arn: str):
        """
        Retrieves information about a resource that was analyzed.
        :param resource_arn: {str} The ARN of the analyzer to retrieve information from.
        :param analyzer_arn: {str} The ARN of the resource to retrieve information about.
        :return: {datamodels.Resource} resource data model.
                raise AWSIAMNotFoundException if analyzed resource was not found
        """
        try:
            response = self.client.get_analyzed_resource(
                analyzerArn=analyzer_arn, resourceArn=resource_arn
            )
        except botocore.exceptions.ClientError as error:
            if (
                error.response.get("Error", {}).get("Code")
                == "ResourceNotFoundException"
            ):
                raise AWSIAMNotFoundException("Analyzed resource not found.")
            raise error
        self.validate_response(
            response, error_msg=f"Failed to get analyzed resource {resource_arn}"
        )
        return self.parser.build_resource_obj(response)

    def get_findings(
        self,
        analyzer_arn: str,
        last_success_time: int,
        sort_by: Optional[str] = "UpdatedAt",
        existing_ids: List[str] = None,
        status: Optional[str] = "ACTIVE",
        limit: Optional[int] = consts.PAGE_SIZE,
        resource_types: List[str] = None,
    ):
        """
        Get analyzer findings page. Findings older than last_success_time param will be returned.
        :param analyzer_arn: {str} The ARN of the analyzer to retrieve findings from.
        :param sort_by: {str} the name of the attribute to sort on.
        :param status: {str} the status of the findings to return.
        :param last_success_time:  {int} unix time to search findings older from.
        :param limit: {int} max findings to return.
        :param existing_ids: {list} already seen finding ids.
        :param resource_types: {list} list of resource types of findings to return.
        :return: {[datamodels.Finding]} list of Findings data models.
                raise AWSIAMStatusCodeException if connectivity failed to validate status code
        """
        pagination_config = {
            # Max results is not specified to filter all findings by time criteria
            "PageSize": min(limit, consts.PAGE_SIZE)  # page size
        }

        paginator = self.client.get_paginator("list_findings")

        filter = {"status": {"eq": [status]}}

        if resource_types:
            filter["resourceType"] = {}
            filter["resourceType"]["contains"] = resource_types

        page_iterator = paginator.paginate(
            analyzerArn=analyzer_arn,
            filter=filter,
            sort={"attributeName": sort_by, "orderBy": consts.DESC},
            PaginationConfig=pagination_config,
        )

        filtered_findings = []

        # Iterate in descending order and return the oldest findings that are greater than last success time
        for page in page_iterator:
            self.validate_response(page, error_msg="Failed to get findings page.")
            new_findings = [
                self.parser.build_finding_obj(finding)
                for finding in page.get("findings", [])
                if convert_datetime_to_unix_time(finding.get("updatedAt"))
                >= last_success_time
            ]

            # Filter already seen alerts
            new_findings = filter_old_alerts(
                self.siemplify, new_findings, existing_ids, id_key="id"
            )

            if not new_findings:
                break
            filtered_findings.extend(new_findings)

        return filtered_findings[-limit:] if limit else filtered_findings
