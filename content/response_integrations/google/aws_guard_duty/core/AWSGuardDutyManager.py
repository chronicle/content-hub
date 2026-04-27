# ============================================================================#
# title           :AWSGuardDutyManager.py
# description     :This Module contain all AWS GuardDuty operations functionality
# author          :avital@siemplify.co
# date            :12-10-2020
# python_version  :3.7
# libraries       :boto3
# requirements    :
# product_version :1.0
# ============================================================================#

# ============================= IMPORTS ===================================== #
from __future__ import annotations
import boto3
import botocore

from .exceptions import (
    AWSGuardDutyStatusCodeException,
    AWSGuardDutyResourceAlreadyExistsException,
    AWSGuardDutyNotFoundException,
)
from .AWSGuardDutyParser import AWSGuardDutyParser
from . import consts
from . import utils


class AWSGuardDutyManager:
    """
    AWS GuardDuty Manager
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
            "guardduty",
            aws_access_key_id=aws_access_key,
            aws_secret_access_key=aws_secret_key,
            region_name=aws_default_region,
            verify=verify_ssl,
        )
        self.parser = AWSGuardDutyParser()

    @staticmethod
    def validate_response(response, error_msg="An error occurred"):
        """
        Validate client Security Hub response status code
        :param error_msg: {str} Error message to display in case of an error
        :param response: client Security Hub response
        :return: raise AWSGuardDutyStatusCodeException if status code is not 200
        """
        if (
            response.get("ResponseMetadata", {}).get("HTTPStatusCode")
            not in AWSGuardDutyManager.VALID_STATUS_CODES
        ):
            raise AWSGuardDutyStatusCodeException(f"{error_msg}. Response: {response}")

    def test_connectivity(self):
        """
        Test connectivity with AWS GuardDuty service
        :return: true if successfully tested connectivity
                raise botocore.exceptions.ClientError if connectivity failed
                raise AWSGuardDutyStatusCodeException if connectivity failed to validate status code
        """
        response = self.client.list_detectors(MaxResults=1)
        self.validate_response(
            response,
            error_msg="Failed to test connectivity with AWS GuardDuty Service.",
        )
        return True

    def get_trusted_ip_lists_ids(self, detector_id, max_results=None):
        """
        Get all trusted IP lists (IPSets) of the GuardDuty service specified by the detector ID.
        :param detector_id: {str} The unique ID of the detector that the IPSet is associated with.
        :param max_results: {int} maximum number of Result Values. Default is 50.
        :return: {list} List of list ids
                raise AWSGuardDutyStatusCodeException if failed to validate response status code
        """
        paginator = self.client.get_paginator("list_ip_sets")
        page_iterator = paginator.paginate(
            DetectorId=detector_id,
            PaginationConfig={
                "MaxItems": (
                    min(max_results, consts.DEFAULT_MAX_RESULTS)
                    if max_results is not None
                    else None
                ),
                "PageSize": consts.PAGE_SIZE,
            },
        )

        list_ids = []

        for page in page_iterator:
            if max_results is not None and len(list_ids) >= max_results:
                break

            self.validate_response(
                page, error_msg="Failed to get trusted IPs lists page."
            )
            list_ids.extend(page.get("IpSetIds", []))

        return list_ids[:max_results] if max_results is not None else list_ids

    def get_threat_intelligence_sets_ids(self, detector_id, max_results=None):
        """
        List available threat intelligence sets in AWS GuardDuty.
        :param detector_id: {str} The unique ID of the detector that the IPSet is associated with.
        :param max_results: {int} maximum number of Result Values. Default is 50.
        :return: {list} List of TI sets ids
                raise AWSGuardDutyStatusCodeException if failed to validate response status code
        """
        paginator = self.client.get_paginator("list_threat_intel_sets")
        page_iterator = paginator.paginate(
            DetectorId=detector_id,
            PaginationConfig={
                "MaxItems": (
                    min(max_results, consts.DEFAULT_MAX_RESULTS)
                    if max_results is not None
                    else None
                ),
                "PageSize": consts.PAGE_SIZE,
            },
        )

        set_ids = []

        for page in page_iterator:
            if max_results is not None and len(set_ids) >= max_results:
                break

            self.validate_response(
                page, error_msg="Failed to get threat intelligence sets page."
            )
            set_ids.extend(page.get("ThreatIntelSetIds", []))

        return set_ids[:max_results] if max_results is not None else set_ids

    def get_findings_page(
        self,
        detector_id,
        min_severity=None,
        updated_at=None,
        page_size=consts.PAGE_SIZE,
        search_after_token=None,
        asc=True,
        sort_by="updatedAt",
    ):
        """
        Get findings single page by various filters.
        :param detector_id: {str} The unique ID of the detector that the IPSet is associated with.
        :param min_severity: {int} Lowest severity that will be used to fetch findings. Possible values are in range from 1 to 8.
        :param updated_at: {int} search for findings that were updated after the given updated time (milliseconds)
        :param page_size: {int} page size
        :param asc: {bool} if true, the findings will be in ascending order, otherwise descending
        :param sort_by: {str} field name to sort the results by
        :param search_after_token: {str} token from where to start fetching next page
        :return: {tuple} ({str} next token, {list} of Finding objects) next token will be None if all findings were fetched
                raise AWSGuardDutyStatusCodeException if failed to validate response status code
                raise AWSGuardDutyValidationException if failed to validate parameters
        """
        pagination_config = {
            # limit the API to return Max findings in page iteration. If more results exist NextToken will be returned
            "MaxItems": page_size,
            "PageSize": page_size,  # page size
        }

        if search_after_token:  # continue previous pagination
            pagination_config["StartingToken"] = search_after_token

        paginator = self.client.get_paginator("list_findings")

        page_iterator = paginator.paginate(
            DetectorId=detector_id,
            FindingCriteria={
                "Criterion": {
                    "service.archived": {"Equals": ["false"]},
                    "severity": {"Gte": min_severity} if min_severity else {},
                    "updatedAt": {"Gte": updated_at} if updated_at else {},
                }
            },
            SortCriteria={
                "AttributeName": sort_by,
                "OrderBy": consts.ASC if asc else consts.DESC,
            },
            PaginationConfig=pagination_config,
        )

        search_after_token = None
        findings_ids = []

        for page in page_iterator:
            self.validate_response(page, error_msg="Failed to get findings page.")
            findings_ids = page.get("FindingIds", [])
            search_after_token = page.get("NextToken")
            break

        return search_after_token, self.get_findings_by_ids(
            detector_id, findings_ids, sort_by=sort_by, asc=asc
        )

    def get_findings_ids_for_detector(
        self, detector_id, sort_by=None, order_by=consts.ASC, max_results=None
    ):
        """
        Lists all Amazon GuardDuty findings for the specified detector ID.
        :param detector_id: {str} The unique ID of the detector that the IPSet is associated with.
        :param order_by: {str} whether to bring results in ascending order or descending order
        :param sort_by: {str} field name to sort the results by
        :param max_results: {int} maximum number of Result Values. Default is 50.
        :return: {list} List of findings ids
                raise AWSGuardDutyStatusCodeException if failed to validate response status code
        """
        paginator = self.client.get_paginator("list_findings")
        pagination_config = {
            "DetectorId": detector_id,
            "PaginationConfig": {
                "MaxItems": (
                    min(max_results, consts.DEFAULT_MAX_RESULTS)
                    if max_results is not None
                    else None
                ),
                "PageSize": consts.PAGE_SIZE,
            },
            "SortCriteria": (
                {"AttributeName": sort_by, "OrderBy": order_by} if sort_by else None
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
            findings_ids.extend(page.get("FindingIds", []))

        return findings_ids[:max_results] if max_results is not None else findings_ids

    def get_findings_by_ids(
        self, detector_id, findings_ids, asc=True, sort_by="updatedAt"
    ):
        """
        Get findings details for a given detector by their IDs
        :param detector_id: {str} The ID of the detector
        :param findings_ids: {list} List of the findings IDs to fetch
        :param asc: {bool} if true, the findings will be in ascending order, otherwise descending
        :param sort_by: {str} field name to sort the results by
        :return: {[datamodels.Finding]} List of the found findings details
        """
        response = self.client.get_findings(
            DetectorId=detector_id,
            FindingIds=findings_ids,
            SortCriteria={
                "AttributeName": sort_by,
                "OrderBy": consts.ASC if asc else consts.DESC,
            },
        )
        self.validate_response(
            response,
            error_msg=f"Unable to get findings details for detector {detector_id}",
        )
        return [
            self.parser.build_siemplify_finding_obj(finding, detector_id)
            for finding in response.get("Findings", [])
        ]

    def get_ip_set_by_id(self, detector_id, ip_set_id):
        """
        Get Ip Set details by its ID
        :param detector_id: {str} The ID of the detector
        :param ip_set_id: {str} The ID of the IP set
        :return: {datamodels.IpSet} The IpSet details
        """
        response = self.client.get_ip_set(DetectorId=detector_id, IpSetId=ip_set_id)
        self.validate_response(
            response, error_msg=f"Unable to get IP Set {ip_set_id} details"
        )
        return self.parser.build_siemplify_ip_set_obj(response, id=ip_set_id)

    def create_ip_set(
        self, detector_id, name, file_format, file_location, activate=True
    ):
        """
        Create an IP Set
        :param detector_id: {str} The ID of the detector
        :param name: {str} Specify the name of the Trusted IP List.
        :param file_format: {str} The format of the file that should be used to create a Trusted IP List
        :param file_location: {str} Specify the URI location, where the file is located.
        :param activate: {bool} If true, the newly created Trusted IP List will be activated.
        :return: {str} The ID of the created IP Set
        """
        response = self.client.create_ip_set(
            DetectorId=detector_id,
            Name=name,
            Format=file_format,
            Location=file_location,
            Activate=activate,
        )
        self.validate_response(response, error_msg="Unable to create IP Set")
        return response.get("IpSetId")

    def update_ip_set(
        self, detector_id, ip_set_id, name=None, file_location=None, activate=True
    ):
        """
        Update an IP Set
        :param detector_id: {str} The ID of the detector
        :param ip_set_id: {str} The ID of the Trusted IP List to update
        :param name: {str} Specify the name of the Trusted IP List.
        :param file_location: {str} Specify the URI location, where the file is located.
        :param activate: {bool} If true, the newly created Trusted IP List will be activated.
        :return: {bool} True if successful, exception otherwise
        """
        params = {
            "DetectorId": detector_id,
            "Name": name,
            "IpSetId": ip_set_id,
            "Location": file_location,
            "Activate": activate,
        }
        response = self.client.update_ip_set(**utils.remove_empty_kwargs(params))
        self.validate_response(
            response, error_msg=f"Unable to update IP Set {ip_set_id}"
        )
        return True

    def delete_ip_set_by_id(self, detector_id, ip_set_id):
        """
        Delete Ip Set by its ID
        :param detector_id: {str} The ID of the detector
        :param ip_set_id: {str} The ID of the IP set
        :return: {bool} True if successful, exception otherwise
        """
        response = self.client.delete_ip_set(DetectorId=detector_id, IpSetId=ip_set_id)
        self.validate_response(
            response, error_msg=f"Unable to delete IP Set {ip_set_id}"
        )
        return True

    def get_threat_intel_set_by_id(self, detector_id, threat_intel_set_id):
        """
        Get TI Set details by its ID
        :param detector_id: {str} The ID of the detector
        :param threat_intel_set_id: {str} The ID of the TI set
        :return: {datamodels.TISet} The TISet details
        """
        response = self.client.get_threat_intel_set(
            DetectorId=detector_id, ThreatIntelSetId=threat_intel_set_id
        )
        self.validate_response(
            response,
            error_msg=f"Unable to get Threat Intelligence set {threat_intel_set_id} details",
        )
        return self.parser.build_siemplify_threat_intel_set_obj(
            response, id=threat_intel_set_id
        )

    def create_threat_intel_set(
        self, detector_id, name, file_format, file_location, activate=True, tags=None
    ):
        """
        Create an Threat Intelligence Set
        :param detector_id: {str} The ID of the detector
        :param name: {str} Specify the name of the Threat Intelligence Set.
        :param file_format: {str} The format of the file that should be used to create a Threat Intelligence set
        :param file_location: {str} Specify the URI location, where the file is located.
        :param activate: {bool} If true, the newly created Threat Intelligence set will be activated.
        :param tags: {dict} The tags to be added to a new threat list resource.
        :return: {str} The ID of the created Threat Intelligence Set
        """
        response = self.client.create_threat_intel_set(
            DetectorId=detector_id,
            Name=name,
            Format=file_format,
            Location=file_location,
            Activate=activate,
            Tags=tags,
        )
        self.validate_response(
            response, error_msg="Unable to create Threat Intelligence Set"
        )
        return response.get("ThreatIntelSetId")

    def update_threat_intel_set(
        self,
        detector_id,
        threat_intel_set_id,
        name=None,
        file_location=None,
        activate=True,
    ):
        """
        Update an Threat Intelligence Set
        :param detector_id: {str} The ID of the detector
        :param threat_intel_set_id: {str} The ID of the Threat Intelligence Set to update
        :param name: {str} Specify the name of the Threat Intelligence Set.
        :param file_location: {str} Specify the URI location, where the file is located.
        :param activate: {bool} If true, the newly created Threat Intelligence Set will be activated.
        :return: {bool} True if successful, exception otherwise
        """
        params = {
            "DetectorId": detector_id,
            "Name": name,
            "ThreatIntelSetId": threat_intel_set_id,
            "Location": file_location,
            "Activate": activate,
        }
        response = self.client.update_threat_intel_set(
            **utils.remove_empty_kwargs(params)
        )
        self.validate_response(
            response,
            error_msg=f"Unable to update Threat Intelligence Set {threat_intel_set_id}",
        )
        return True

    def delete_threat_intel_set_by_id(self, detector_id, threat_intel_set_id):
        """
        Delete TI Set by its ID
        :param detector_id: {str} The ID of the detector
        :param threat_intel_set_id: {str} The ID of the TI set
        :return: {bool} True if successful, exception otherwise
        """
        response = self.client.delete_threat_intel_set(
            DetectorId=detector_id, ThreatIntelSetId=threat_intel_set_id
        )
        self.validate_response(
            response,
            error_msg=f"Unable to delete Threat Intelligence set {threat_intel_set_id}",
        )
        return True

    def create_detector(self, enable=False):
        """
        Creates a single Amazon GuardDuty detector. A detector is a resource that represents the GuardDuty service.
        To start using GuardDuty, you must create a detector in each Region where you enable the service. You can have
        only one detector per account per Region. All data sources are enabled in a new detector by default.
        :param enable: {bool} A Boolean value that specifies whether the detector is to be enabled.
        :return: {str} The ID of the created detector
        """
        try:
            response = self.client.create_detector(Enable=enable)
            self.validate_response(response, error_msg="Unable to create detector")
            return response.get("DetectorId")
        except botocore.exceptions.ClientError as error:
            if error.response.get("Error", {}).get("Code") == "BadRequestException":
                raise AWSGuardDutyResourceAlreadyExistsException(
                    f"Unable to create detector."
                    f" Reason: {error.response.get('Message')}"
                )

            raise

    def delete_detector(self, detector_id):
        """
        Deletes an Amazon GuardDuty detector that is specified by the detector ID.
        :param detector_id: {str} The unique ID of the detector that you want to delete.
        :return: {bool} True if successful, exception otherwise
        """
        response = self.client.delete_detector(DetectorId=detector_id)
        self.validate_response(
            response, error_msg=f"Unable to delete detector {detector_id}"
        )
        return True

    def get_detector(self, detector_id):
        """
        Deletes an Amazon GuardDuty detector that is specified by the detector ID.
        :param detector_id: {str} The unique ID of the detector that you want to delete.
        :return: {bool} True if successful, exception otherwise
        """
        response = self.client.get_detector(DetectorId=detector_id)
        self.validate_response(
            response, error_msg=f"Unable to get detector {detector_id}"
        )
        return self.parser.build_siemplify_detector_obj(response, id=detector_id)

    def update_detector(self, detector_id, enable=False):
        """
        Update the Amazon GuardDuty detector specified by the detector ID.
        :param detector_id: {str} The unique ID of the detector that you want to update.
        :param enable: {bool} Specifies whether the detector should be enabled
        :return: {bool} True if successful, exception otherwise
        """
        response = self.client.update_detector(DetectorId=detector_id, Enable=enable)
        self.validate_response(
            response, error_msg=f"Unable to update detector {detector_id}"
        )
        return True

    def list_detectors(self, max_results=None, page_size=consts.PAGE_SIZE):
        """
        Lists detectorIds of all the existing Amazon GuardDuty detector resources.
        :param page_size:
        :param max_results: {int} Specify how many detectors to return. Default is 50.
        :return: {list} List of detector Ids of all the existing Amazon GuardDuty detector resources.
        """
        pagination_config = {
            # limit the API to return Max findings in page iteration. If more results exist NextToken will be returned
            "MaxItems": (
                min(max_results, consts.DEFAULT_MAX_RESULTS)
                if max_results is not None
                else None
            ),
            "PageSize": page_size,
        }

        paginator = self.client.get_paginator("list_detectors")

        detector_ids = []

        page_iterator = paginator.paginate(PaginationConfig=pagination_config)

        for page in page_iterator:
            if max_results is not None and len(detector_ids) >= max_results:
                break

            self.validate_response(page, error_msg="Unable to list detectors.")
            detector_ids.extend(page.get("DetectorIds", []))

        return detector_ids

    def get_detector_details(self, detector_id):
        """
        Retrieve an Amazon GuardDuty detector specified by the detector ID.
        :param detector_id: {str} The unique ID of the detector that you want to retrieve. Comma separated values
        :return: {datamodels.Detector} if successful, exception otherwise.
        """
        response = self.client.get_detector(DetectorId=detector_id)
        self.validate_response(
            response,
            error_msg=f"Unable to get detector details for detector {detector_id}",
        )
        return self.parser.build_siemplify_detector_obj(response, id=detector_id)

    def archive_findings(self, detector_id, finding_ids):
        """
        Archive GuardDuty findings that are specified by finding IDs.
        :param detector_id: {str} The unique ID of the detector.
        :param finding_ids: {list} The IDs of the findings that you want to archive. Comma separated ids.
        :return: {bool} True if successful, exception otherwise
        """
        response = self.client.archive_findings(
            DetectorId=detector_id, FindingIds=finding_ids
        )
        self.validate_response(response, error_msg="Unable to archive findings")
        return True

    def unarchive_findings(self, detector_id, finding_ids):
        """
        Unarchive GuardDuty findings that are specified by finding IDs..
        :param detector_id: {str} The unique ID of the detector.
        :param finding_ids: {list} The IDs of the findings that you want to unarchive. Comma separated ids.
        :return: {bool} True if successful, exception otherwise
        """
        response = self.client.unarchive_findings(
            DetectorId=detector_id, FindingIds=finding_ids
        )
        self.validate_response(response, error_msg="Unable to un-archive findings")
        return True

    def create_sample_findings(self, detector_id, finding_types):
        """
        Generates example findings of types specified by the list of findings.
        :param detector_id: {str} The unique ID of the detector to create sample findings for.
        :param finding_types: {list} The types of sample findings to generate. Comma separated values.
        :return: {bool} True if successful, exception otherwise
        """
        try:
            response = self.client.create_sample_findings(
                DetectorId=detector_id, FindingTypes=finding_types
            )
            self.validate_response(
                response, error_msg="Action wasn’t able to create sample findings."
            )
            return True

        except botocore.exceptions.ClientError as error:
            exception_message = (
                "The request is rejected because an invalid or out-of-range value is specified as an"
                " input parameter."
            )
            if exception_message in error.response.get("Message"):
                raise AWSGuardDutyNotFoundException(error.response.get("Message"))

            raise

    def update_findings_feedback(self, detector_id, useful, finding_ids, comment):
        """
        Mark the specified Amazon GuardDuty findings as useful or not useful.
        :param detector_id: {str} The unique ID of the detector associated with the findings to update feedback for.
        :param useful: {bool} The feedback for the finding.
        :param finding_ids: {list} The IDs of the findings that you want to mark as useful or not useful. Comma separated values.
        :param comment: {str} Additional feedback about the GuardDuty findings.
        :return: {bool} True if successful, exception otherwise
        """
        params = {
            "DetectorId": detector_id,
            "Feedback": useful,
            "FindingIds": finding_ids,
            "Comments": comment,
        }
        response = self.client.update_findings_feedback(
            **utils.remove_empty_kwargs(params)
        )
        self.validate_response(response, error_msg="Unable to update findings feedback")
        return True
