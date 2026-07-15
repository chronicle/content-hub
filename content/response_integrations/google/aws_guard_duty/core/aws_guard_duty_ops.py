# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""AWS GuardDuty mixin operations."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import botocore

from . import consts, utils
from .exceptions import (
    AWSGuardDutyNotFoundError,
    AWSGuardDutyResourceAlreadyExistsError,
)

if TYPE_CHECKING:
    import boto3

    from .datamodels import Detector, Finding, FindingsQuery, IpSet, TISet


class AWSGuardDutyBaseOperations:
    """Base class for all AWS GuardDuty mixin operations."""

    client: boto3.client
    parser: Any


class DetectorOperationsMixin(AWSGuardDutyBaseOperations):
    """Detector operations mixin class."""

    def create_detector(self, *, enable: bool = False) -> str:
        """Create a single Amazon GuardDuty detector.

        Args:
            enable: A Boolean value that specifies whether the detector is to
              be enabled.

        Returns:
            The ID of the created detector.

        Raises:
            AWSGuardDutyResourceAlreadyExistsError: If detector already exists.
            botocore.exceptions.ClientError: If the AWS GuardDuty service returns a client error.

        """
        try:
            response = self.client.create_detector(Enable=enable)
            utils.validate_response(response, error_msg="Unable to create detector")
            return response.get("DetectorId")
        except botocore.exceptions.ClientError as error:
            if error.response.get("Error", {}).get("Code") == "BadRequestException":
                msg = f"Unable to create detector. Reason: {error.response.get('Message')}"
                raise AWSGuardDutyResourceAlreadyExistsError(msg) from error

            raise

    def delete_detector(self, detector_id: str) -> bool:
        """Delete an Amazon GuardDuty detector that is specified by the detector ID.

        Args:
            detector_id: The unique ID of the detector to delete.

        Returns:
            True if successful.

        """
        response = self.client.delete_detector(DetectorId=detector_id)
        utils.validate_response(response, error_msg=f"Unable to delete detector {detector_id}")
        return True

    def get_detector(self, detector_id: str) -> Detector:
        """Get details of a detector specified by detector ID.

        Args:
            detector_id: The unique ID of the detector to retrieve.

        Returns:
            Detector details.

        """
        response = self.client.get_detector(DetectorId=detector_id)
        utils.validate_response(response, error_msg=f"Unable to get detector {detector_id}")
        return self.parser.build_siemplify_detector_obj(response, detector_id=detector_id)

    def update_detector(self, detector_id: str, *, enable: bool = False) -> bool:
        """Update the Amazon GuardDuty detector specified by the detector ID.

        Args:
            detector_id: The unique ID of the detector to update.
            enable: Specifies whether the detector should be enabled.

        Returns:
            True if successful.

        """
        response = self.client.update_detector(DetectorId=detector_id, Enable=enable)
        utils.validate_response(response, error_msg=f"Unable to update detector {detector_id}")
        return True

    def list_detectors(self, max_results: int | None = None, page_size: int = consts.PAGE_SIZE) -> list[str]:
        """List detectorIds of all existing Amazon GuardDuty detectors.

        Args:
            max_results: Maximum number of detectors to return.
            page_size: Size of pages to retrieve.

        Returns:
            List of detector IDs.

        """
        pagination_config = {
            "MaxItems": (min(max_results, consts.DEFAULT_MAX_RESULTS) if max_results is not None else None),
            "PageSize": page_size,
        }

        paginator = self.client.get_paginator("list_detectors")

        detector_ids = []

        page_iterator = paginator.paginate(PaginationConfig=pagination_config)

        for page in page_iterator:
            if max_results is not None and len(detector_ids) >= max_results:
                break

            utils.validate_response(page, error_msg="Unable to list detectors.")
            detector_ids.extend(page.get("DetectorIds", []))

        return detector_ids

    def get_detector_details(self, detector_id: str) -> Detector:
        """Retrieve details of an Amazon GuardDuty detector specified by detector ID.

        Args:
            detector_id: The unique ID of the detector to retrieve.

        Returns:
            Detector details.

        """
        response = self.client.get_detector(DetectorId=detector_id)
        utils.validate_response(
            response,
            error_msg=f"Unable to get detector details for detector {detector_id}",
        )
        return self.parser.build_siemplify_detector_obj(response, detector_id=detector_id)


class IPSetOperationsMixin(AWSGuardDutyBaseOperations):
    """IP Set operations mixin class."""

    def get_trusted_ip_lists_ids(
        self,
        detector_id: str,
        max_results: int | None = None,
        page_size: int = consts.PAGE_SIZE,
    ) -> list[str]:
        """List IPSetIds of all existing IP Sets (trusted IP list) for a detector.

        Args:
            detector_id: The unique ID of the detector.
            max_results: Maximum number of IP sets to return.
            page_size: Size of pages to retrieve.

        Returns:
            List of IP Set IDs.

        """
        pagination_config = {
            "MaxItems": (min(max_results, consts.DEFAULT_MAX_RESULTS) if max_results is not None else None),
            "PageSize": page_size,
        }

        paginator = self.client.get_paginator("list_ip_sets")
        set_ids = []
        page_iterator = paginator.paginate(DetectorId=detector_id, PaginationConfig=pagination_config)

        for page in page_iterator:
            if max_results is not None and len(set_ids) >= max_results:
                break

            utils.validate_response(page, error_msg="Failed to get trusted IP lists page.")
            set_ids.extend(page.get("IpSetIds", []))

        return set_ids[:max_results] if max_results is not None else set_ids

    def get_ip_set_by_id(self, detector_id: str, ip_set_id: str) -> IpSet:
        """Retrieve details of an IP Set specified by its ID.

        Args:
            detector_id: The unique ID of the detector.
            ip_set_id: The ID of the IP Set.

        Returns:
            IP Set details.

        """
        response = self.client.get_ip_set(DetectorId=detector_id, IpSetId=ip_set_id)
        utils.validate_response(
            response,
            error_msg=f"Unable to get trusted IP list details for list ID: {ip_set_id}",
        )
        return self.parser.build_siemplify_ip_set_obj(response, ip_set_id=ip_set_id)

    def create_ip_set(
        self,
        detector_id: str,
        name: str,
        file_format: str,
        location: str,
        *,
        activate: bool = False,
    ) -> str:
        """Create a new IP Set (trusted IP list).

        Args:
            detector_id: The unique ID of the detector.
            name: Name of the IP Set.
            file_format: Format of the IP list (e.g. TXT, STIX, etc.).
            location: The URI location of the file containing IP list.
            activate: If True, the IP Set will be activated.

        Returns:
            The ID of the created IP Set.

        """
        response = self.client.create_ip_set(
            DetectorId=detector_id,
            Name=name,
            Format=file_format,
            Location=location,
            Activate=activate,
        )
        utils.validate_response(response, error_msg="Unable to create trusted IP list.")
        return response.get("IpSetId")

    def update_ip_set(
        self,
        detector_id: str,
        ip_set_id: str,
        name: str | None = None,
        location: str | None = None,
        *,
        activate: bool = False,
    ) -> bool:
        """Update an existing IP Set (trusted IP list).

        Args:
            detector_id: The unique ID of the detector.
            ip_set_id: The ID of the IP Set to update.
            name: New name of the IP Set.
            location: New URI location of the IP list file.
            activate: If True, the IP Set will be activated.

        Returns:
            True if successful.

        """
        params = {
            "DetectorId": detector_id,
            "IpSetId": ip_set_id,
            "Name": name,
            "Location": location,
            "Activate": activate,
        }
        response = self.client.update_ip_set(**utils.remove_empty_kwargs(params))
        utils.validate_response(
            response,
            error_msg=f"Unable to update trusted IP list for list ID: {ip_set_id}",
        )
        return True

    def delete_ip_set_by_id(self, detector_id: str, ip_set_id: str) -> bool:
        """Delete an IP Set (trusted IP list) specified by its ID.

        Args:
            detector_id: The unique ID of the detector.
            ip_set_id: The ID of the IP Set to delete.

        Returns:
            True if successful.

        """
        response = self.client.delete_ip_set(DetectorId=detector_id, IpSetId=ip_set_id)
        utils.validate_response(
            response,
            error_msg=f"Unable to delete trusted IP list for list ID: {ip_set_id}",
        )
        return True


class ThreatIntelSetOperationsMixin(AWSGuardDutyBaseOperations):
    """Threat Intel Set operations mixin class."""

    def get_threat_intelligence_sets_ids(
        self,
        detector_id: str,
        max_results: int | None = None,
        page_size: int = consts.PAGE_SIZE,
    ) -> list[str]:
        """List ThreatIntelSetIds of all existing Threat Intelligence sets for a detector.

        Args:
            detector_id: The unique ID of the detector.
            max_results: Maximum number of sets to return.
            page_size: Size of pages to retrieve.

        Returns:
            List of Threat Intel Set IDs.

        """
        pagination_config = {
            "MaxItems": (min(max_results, consts.DEFAULT_MAX_RESULTS) if max_results is not None else None),
            "PageSize": page_size,
        }

        paginator = self.client.get_paginator("list_threat_intel_sets")
        set_ids = []
        page_iterator = paginator.paginate(DetectorId=detector_id, PaginationConfig=pagination_config)

        for page in page_iterator:
            if max_results is not None and len(set_ids) >= max_results:
                break

            utils.validate_response(page, error_msg="Failed to get threat intelligence sets page.")
            set_ids.extend(page.get("ThreatIntelSetIds", []))

        return set_ids[:max_results] if max_results is not None else set_ids

    def get_threat_intel_set_by_id(self, detector_id: str, threat_intel_set_id: str) -> TISet:
        """Retrieve details of a Threat Intelligence Set specified by its ID.

        Args:
            detector_id: The ID of the detector.
            threat_intel_set_id: The ID of the Threat Intel set.

        Returns:
            Threat Intel set details.

        """
        response = self.client.get_threat_intel_set(DetectorId=detector_id, ThreatIntelSetId=threat_intel_set_id)
        utils.validate_response(
            response,
            error_msg=(f"Unable to get Threat Intelligence list details for list ID: {threat_intel_set_id}"),
        )
        return self.parser.build_siemplify_threat_intel_set_obj(response, ti_set_id=threat_intel_set_id)

    def create_threat_intel_set(
        self,
        detector_id: str,
        ti_set: TISet,
        *,
        activate: bool = True,
    ) -> str:
        """Create a Threat Intelligence Set.

        Args:
            detector_id: The ID of the detector.
            ti_set: TISet instance.
            activate: If True, the Threat Intelligence set will be activated.

        Returns:
            The ID of the created Threat Intelligence Set.

        """
        response = self.client.create_threat_intel_set(
            DetectorId=detector_id,
            Name=ti_set.name,
            Format=ti_set.format,
            Location=ti_set.location,
            Activate=activate,
            Tags=ti_set.tags,
        )
        utils.validate_response(response, error_msg="Unable to create Threat Intelligence Set")
        return response.get("ThreatIntelSetId")

    def update_threat_intel_set(
        self,
        detector_id: str,
        threat_intel_set_id: str,
        name: str | None = None,
        file_location: str | None = None,
        *,
        activate: bool = True,
    ) -> bool:
        """Update a Threat Intelligence Set.

        Args:
            detector_id: The ID of the detector.
            threat_intel_set_id: The ID of the Threat Intelligence Set to update.
            name: Specify the name of the Threat Intelligence Set.
            file_location: Specify the URI location where the file is located.
            activate: If True, the Threat Intelligence Set will be activated.

        Returns:
            True if successful.

        """
        params = {
            "DetectorId": detector_id,
            "Name": name,
            "ThreatIntelSetId": threat_intel_set_id,
            "Location": file_location,
            "Activate": activate,
        }
        response = self.client.update_threat_intel_set(**utils.remove_empty_kwargs(params))
        utils.validate_response(
            response,
            error_msg="Unable to update Threat Intelligence list: " + threat_intel_set_id,
        )
        return True

    def delete_threat_intel_set_by_id(self, detector_id: str, threat_intel_set_id: str) -> bool:
        """Delete Threat Intelligence Set by its ID.

        Args:
            detector_id: The ID of the detector.
            threat_intel_set_id: The ID of the TI set.

        Returns:
            True if successful.

        """
        response = self.client.delete_threat_intel_set(DetectorId=detector_id, ThreatIntelSetId=threat_intel_set_id)
        utils.validate_response(
            response,
            error_msg=f"Unable to delete Threat Intelligence set {threat_intel_set_id}",
        )
        return True


class FindingsOperationsMixin(AWSGuardDutyBaseOperations):
    """Findings operations mixin class."""

    def get_findings_page(
        self,
        query: FindingsQuery,
    ) -> tuple[str | None, list[Finding]]:
        """Get findings single page by various filters.

        Args:
            query: FindingsQuery instance.

        Returns:
            A tuple containing the next token (or None if finished) and
            a list of Finding objects.

        """
        detector_id = query.detector_id
        min_severity = query.min_severity
        updated_at = query.updated_at
        page_size = query.page_size
        search_after_token = query.search_after_token
        asc = query.asc
        sort_by = query.sort_by
        pagination_config = {
            "MaxItems": page_size,
            "PageSize": page_size,
        }

        if search_after_token:
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
            utils.validate_response(page, error_msg="Failed to get findings page.")
            findings_ids = page.get("FindingIds", [])
            search_after_token = page.get("NextToken")
            break

        return search_after_token, self.get_findings_by_ids(detector_id, findings_ids, sort_by=sort_by, asc=asc)

    def get_findings_ids_for_detector(
        self,
        detector_id: str,
        sort_by: str | None = None,
        order_by: str = consts.ASC,
        max_results: int | None = None,
    ) -> list[str]:
        """List all Amazon GuardDuty findings IDs for the specified detector ID.

        Args:
            detector_id: The unique ID of the detector.
            sort_by: Field name to sort the results by.
            order_by: Whether to bring results in ascending or descending order.
            max_results: Maximum number of finding IDs to return.

        Returns:
            List of finding IDs.

        """
        pagination_config = {
            "MaxItems": (min(max_results, consts.DEFAULT_MAX_RESULTS) if max_results is not None else None),
            "PageSize": consts.PAGE_SIZE,
        }

        sort_criteria = {}
        if sort_by:
            sort_criteria = {"AttributeName": sort_by, "OrderBy": order_by}

        paginator = self.client.get_paginator("list_findings")

        findings_ids = []

        page_iterator = paginator.paginate(
            DetectorId=detector_id,
            SortCriteria=sort_criteria,
            PaginationConfig=pagination_config,
        )

        for page in page_iterator:
            if max_results is not None and len(findings_ids) >= max_results:
                break

            utils.validate_response(page, error_msg="Unable to list findings.")
            findings_ids.extend(page.get("FindingIds", []))

        return findings_ids

    def get_findings_by_ids(
        self,
        detector_id: str,
        findings_ids: list[str],
        sort_by: str | None = None,
        *,
        asc: bool = True,
    ) -> list[Finding]:
        """Get details of Amazon GuardDuty findings specified by findings IDs.

        Args:
            detector_id: The unique ID of the detector.
            findings_ids: List of finding IDs.
            sort_by: Field name to sort the results by.
            asc: If True, findings are returned in ascending order.

        Returns:
            List of Finding details.

        """
        if not findings_ids:
            return []

        response = self.client.get_findings(
            DetectorId=detector_id,
            FindingIds=findings_ids,
            SortCriteria={
                "AttributeName": sort_by or "updatedAt",
                "OrderBy": consts.ASC if asc else consts.DESC,
            },
        )
        utils.validate_response(response, error_msg="Unable to get findings.")
        return self.parser.build_siemplify_findings_list_obj(response, detector_id=detector_id)

    def archive_findings(self, detector_id: str, finding_ids: list[str]) -> bool:
        """Archive GuardDuty findings that are specified by finding IDs.

        Args:
            detector_id: The unique ID of the detector.
            finding_ids: List of finding IDs.

        Returns:
            True if successful.

        """
        response = self.client.archive_findings(DetectorId=detector_id, FindingIds=finding_ids)
        utils.validate_response(response, error_msg=f"Unable to archive findings for detector {detector_id}")
        return True

    def unarchive_findings(self, detector_id: str, finding_ids: list[str]) -> bool:
        """Un-archive GuardDuty findings that are specified by finding IDs.

        Args:
            detector_id: The unique ID of the detector.
            finding_ids: List of finding IDs.

        Returns:
            True if successful.

        """
        response = self.client.unarchive_findings(DetectorId=detector_id, FindingIds=finding_ids)
        utils.validate_response(
            response,
            error_msg=f"Unable to un-archive findings for detector {detector_id}",
        )
        return True

    def create_sample_findings(self, detector_id: str, finding_types: list[str]) -> bool:
        """Generate example findings of types specified by the list of findings.

        Args:
            detector_id: The unique ID of the detector.
            finding_types: List of finding types.

        Returns:
            True if successful.

        Raises:
            AWSGuardDutyNotFoundError: If an invalid value was found as parameter.
            botocore.exceptions.ClientError: If client error.

        """
        try:
            response = self.client.create_sample_findings(DetectorId=detector_id, FindingTypes=finding_types)
            utils.validate_response(
                response,
                error_msg=(f"Unable to create sample findings for detector {detector_id}"),
            )
        except botocore.exceptions.ClientError as error:
            if error.response.get("Error", {}).get("Code") == "BadRequestException":
                raise AWSGuardDutyNotFoundError(error.response.get("Message")) from error

            raise
        else:
            return True

    def update_findings_feedback(self, detector_id: str, useful: str, finding_ids: list, comment: str) -> bool:
        """Mark the specified Amazon GuardDuty findings as useful or not useful.

        Args:
            detector_id: The unique ID of the detector.
            useful: Usefulness status (Useful/Not Useful).
            finding_ids: The IDs of the findings to update feedback for.
            comment: Additional feedback comment.

        Returns:
            True if successful.

        """
        params = {
            "DetectorId": detector_id,
            "Feedback": useful,
            "FindingIds": finding_ids,
            "Comments": comment,
        }
        response = self.client.update_findings_feedback(**utils.remove_empty_kwargs(params))
        utils.validate_response(response, error_msg="Unable to update findings feedback")
        return True
