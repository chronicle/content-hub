# ============================================================================#
# title           :AmazonMacieManager.py
# description     :This Module contain all Amazon Macie operations functionality
# author          :avital@siemplify.co
# date            :28-10-2020
# python_version  :3.7
# libraries       :boto3
# requirements    :
# product_version :1.0
# ============================================================================#

# ============================= IMPORTS ===================================== #
from __future__ import annotations
import boto3
from . import consts
from . import utils
from .AmazonMacieParser import AmazonMacieParser
from .exceptions import AmazonMacieStatusCodeException


class AmazonMacieManager:
    """
    Amazon Macie Manager
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
            "macie2",
            aws_access_key_id=aws_access_key,
            aws_secret_access_key=aws_secret_key,
            region_name=aws_default_region,
            verify=verify_ssl,
        )
        self.parser = AmazonMacieParser()

    @staticmethod
    def validate_response(response, error_msg="An error occurred"):
        """
        Validate client Amazon Macie response status code
        :param error_msg: {str} Error message to display in case of an error
        :param response: client Amazon Macie response
        :return: raise AmazonMacieStatusCodeException if status code is not 200
        """
        if (
            response.get("ResponseMetadata", {}).get("HTTPStatusCode")
            not in AmazonMacieManager.VALID_STATUS_CODES
        ):
            raise AmazonMacieStatusCodeException(f"{error_msg}. Response: {response}")

    def test_connectivity(self):
        """
        Test connectivity with Amazon Macie service
        :return: true if successfully tested connectivity
                raise botocore.exceptions.ClientError if connectivity failed
                raise AmazonMacieStatusCodeException if connectivity failed to validate status code
        """
        response = self.client.list_findings(maxResults=1)
        self.validate_response(
            response, error_msg="Failed to test connectivity with Amazon Macie Service."
        )
        return True

    def get_findings_page(
        self,
        severities=None,
        updated_at=None,
        finding_types=None,
        page_size=consts.PAGE_SIZE,
        include_archived=False,
        search_after_token=None,
        asc=True,
        sort_by="updatedAt",
    ):
        """
        Get findings single page by various filters.
        :param severities: {list} Finding severity to ingest - High, Medium or Low. If nothing is specified - ingest all
            findings regardless of severity.
        :param finding_types: {list} Finding type to search for, for example SensitiveData:S3Object/Credentials or
            SensitiveData:S3Object/Multiple. If nothing is specified - return all types of findings.
        :param updated_at: {int} search for findings that were updated after the given updated time (milliseconds)
        :param page_size: {int} page size
        :param include_archived: {bool} Specify whether to include archived findings in results or not.
        :param asc: {bool} if true, the findings will be in ascending order, otherwise descending
        :param sort_by: {str} field name to sort the results by
        :param search_after_token: {str} token from where to start fetching next page
        :return: {tuple} ({str} next token, {list} of Finding objects) next token will be None if all findings were fetched
                raise AmazonMacieStatusCodeException if failed to validate response status code
                raise AmazonMacieValidationException if failed to validate parameters
        """

        paginator = self.client.get_paginator("list_findings")
        search_criterion = {
            "updatedAt": {"gte": updated_at} if updated_at else None,
            "archived": {"eq": [str(include_archived).lower()]},
            "type": {"eq": finding_types} if finding_types else None,
            "severity.description": {"eq": severities} if severities else None,
        }

        pagination_config = {
            "findingCriteria": {
                "criterion": utils.remove_empty_kwargs(search_criterion)
            },
            "PaginationConfig": {"MaxItems": page_size, "PageSize": page_size},
            "sortCriteria": (
                {
                    "attributeName": sort_by,
                    "orderBy": consts.ASC if asc else consts.DESC,
                }
                if sort_by
                else None
            ),
        }

        if search_after_token:  # continue previous pagination
            pagination_config["PaginationConfig"]["StartingToken"] = search_after_token

        page_iterator = paginator.paginate(
            **utils.remove_empty_kwargs(pagination_config)
        )

        search_after_token = None
        findings_ids = []

        for page in page_iterator:
            self.validate_response(page, error_msg="Failed to get findings page.")
            findings_ids.extend(page.get("findingIds", []))
            search_after_token = page.get("nextToken")
            break

        return search_after_token, self.get_findings_by_ids(
            findings_ids, sort_by=sort_by, asc=asc
        )

    def get_findings_ids(
        self,
        finding_types=None,
        severities=None,
        time_filter=None,
        include_archived=False,
        sort_by=None,
        order_by=consts.ASC,
        max_results=None,
    ):
        """
        Lists all Amazon Macie findings IDs.
        :param finding_types: {list} Finding type to search for, for example SensitiveData:S3Object/Credentials or
            SensitiveData:S3Object/Multiple. If nothing is specified - return all types of findings.
        :param severities: {list} Finding severity to ingest - High, Medium or Low. If nothing is specified - ingest all
            findings regardless of severity.
        :param time_filter: {int} Filter findings that were updated after given unix timestamp
        :param include_archived: {bool} Specify whether to include archived findings in results or not.
        :param order_by: {str} whether to bring results in ascending order or descending order
        :param sort_by: {str} field name to sort the results by
        :param max_results: {int} maximum number of Result Values. Default is 20.
        :return: {list} List of findings ids
                raise AmazonMacieStatusCodeException if failed to validate response status code
        """
        paginator = self.client.get_paginator("list_findings")
        search_criterion = {
            "updatedAt": {"gte": time_filter} if time_filter else None,
            "archived": {"eq": [str(include_archived).lower()]},
            "type": {"eq": finding_types} if finding_types else None,
            "severity.description": {"eq": severities} if severities else None,
        }

        pagination_config = {
            "findingCriteria": {
                "criterion": utils.remove_empty_kwargs(search_criterion)
            },
            "PaginationConfig": {
                "MaxItems": (
                    min(max_results, consts.DEFAULT_MAX_RESULTS)
                    if max_results is not None
                    else None
                ),
                "PageSize": consts.PAGE_SIZE,
            },
            "sortCriteria": (
                {"attributeName": sort_by, "orderBy": order_by} if sort_by else None
            ),
        }

        page_iterator = paginator.paginate(
            **utils.remove_empty_kwargs(pagination_config)
        )

        findings_ids = []

        for page in page_iterator:
            if max_results is not None and len(findings_ids) >= max_results:
                break

            self.validate_response(page, error_msg="Failed to findings page.")
            findings_ids.extend(page.get("findingIds", []))

        return findings_ids[:max_results] if max_results is not None else findings_ids

    def get_findings_by_ids(self, findings_ids, asc=True, sort_by="updatedAt"):
        """
        Get findings details by their IDs
        :param findings_ids: {list} List of the findings IDs to fetch
        :param asc: {bool} if true, the findings will be in ascending order, otherwise descending
        :param sort_by: {str} field name to sort the results by
        :return: {[datamodels.Finding]} List of the found findings details
        """
        if not findings_ids:
            return []

        response = self.client.get_findings(
            findingIds=findings_ids,
            sortCriteria={
                "attributeName": sort_by,
                "orderBy": consts.ASC if asc else consts.DESC,
            },
        )
        self.validate_response(response, error_msg=f"Unable to get findings details")
        return [
            self.parser.build_siemplify_finding_obj(finding)
            for finding in response.get("findings", [])
        ]

    def enable_macie(self):
        """
        Enables Amazon Macie and specifies the configuration settings for a Macie account.
        :return: {bool} True if successfully enabled macie
            raise AmazonMacieStatusCodeException if failed to validate response status code
        """
        response = self.client.enable_macie()
        self.validate_response(response, error_msg="Failed to enable macie")
        return True

    def disable_macie(self):
        """
        Disables an Amazon Macie account and deletes Macie resources for the account.
        :return: {bool} True if successfully disabled macie
            raise AmazonMacieStatusCodeException if failed to validate response status code
        """
        response = self.client.disable_macie()
        self.validate_response(response, error_msg="Failed to disable macie")
        return True

    def create_custom_data_identifier(
        self,
        name,
        regex,
        description=None,
        ignore_words=None,
        keywords=None,
        maximum_match_distance=None,
        tags=None,
    ):
        """
        Creates and defines the criteria and other settings for a custom data identifier.
        :param name: {str} A custom name for the custom data identifier. The name can contain as many as 128 characters.
        :param regex: {str} The regular expression (regex ) that defines the pattern to match. The expression can contain
                    as many as 512 characters.
        :param description: {str} A custom description of the custom data identifier. The description can contain as
                    many as 512 characters.
        :param ignore_words: {list} An array that lists specific character sequences (ignore words) to exclude from the results.
                    If the text matched by the regular expression is the same as any string in this array, Amazon Macie ignores it.
                    The array can contain as many as 10 ignore words. Each ignore word can contain 4 - 90 characters.
                    Ignore words are case sensitive.
        :param keywords: {list} An array that lists specific character sequences (keywords), one of which must be within proximity
                    (maximumMatchDistance) of the regular expression to match. The array can contain as many as 50 keywords.
                    Each keyword can contain 4 - 90 characters. Keywords aren't case sensitive.
        :param maximum_match_distance: {int} The maximum number of characters that can exist between text that matches
                    the regex pattern
                    and the character sequences specified by the keywords array. Macie includes or excludes a result
                    based on the proximity of a keyword to text that matches the regex pattern.
                    The distance can be 1 - 300 characters. The default value is 50.
        :param tags: {dict} A map of key-value pairs that specifies the tags to associate with the custom data identifier.
        :return: {str} The specified custom data identifier was created.
            raise AmazonMacieStatusCodeException if failed to validate response status code
        """
        params = {
            "description": description,
            "name": name,
            "regex": regex,
            "maximumMatchDistance": maximum_match_distance,
            "tags": tags,
            "keywords": keywords,
            "ignoreWords": ignore_words,
        }
        response = self.client.create_custom_data_identifier(
            **utils.remove_empty_kwargs(params)
        )
        self.validate_response(
            response, error_msg="Failed to create custom data identifier"
        )
        return self.parser.build_siemplify_data_identifier(response)

    def delete_custom_data_identifier(self, custom_data_id):
        """
        Soft deletes a custom data identifier.
        :param id: {str} The unique identifier for the Amazon Macie resource or account that the request applies to.
        :return: {bool} True if successfully deleted custom data identifier
            raise AmazonMacieStatusCodeException if failed to validate response status code
        """
        response = self.client.delete_custom_data_identifier(id=custom_data_id)
        self.validate_response(
            response, error_msg="Failed to delete custom data identifier"
        )
        return True
