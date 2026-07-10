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

from __future__ import annotations

from typing import Any

from .datamodels import Detector, Finding, IpSet, TISet


class AWSGuardDutyParser:
    """AWS Guard Duty Transformation Layer."""

    @staticmethod
    def build_siemplify_finding_obj(raw_data: dict[str, Any], detector_id: str) -> Finding:
        """Build Siemplify Finding object from raw data.

        Args:
            raw_data: Raw JSON response of single element in 'Findings' raw
                data response.
            detector_id: Detector ID using which the data was retrieved.

        Returns:
            Finding data model.

        """
        return Finding(raw_data, detector_id=detector_id)

    @staticmethod
    def build_siemplify_ip_set_obj(raw_data: dict[str, Any], ip_set_id: str | None = None) -> IpSet:
        """Build Siemplify IpSet object from raw data.

        Args:
            raw_data: Raw JSON response of single element in 'IpSet' raw data
                response.
            ip_set_id: The ID of the IP set.

        Returns:
            IpSet data model.

        """
        return IpSet(raw_data, ip_set_id=ip_set_id)

    @staticmethod
    def build_siemplify_threat_intel_set_obj(raw_data: dict[str, Any], ti_set_id: str | None = None) -> TISet:
        """Build Siemplify TISet object from raw data.

        Args:
            raw_data: Raw JSON response of single element in 'threatIntelSet'
                raw data response.
            ti_set_id: The ID of the threat intel set.

        Returns:
            TISet data model.

        """
        return TISet(raw_data, ti_set_id=ti_set_id)

    @staticmethod
    def build_siemplify_detector_obj(raw_data: dict[str, Any], detector_id: str | None = None) -> Detector:
        """Build Siemplify Detector object from raw data.

        Args:
            raw_data: Raw JSON response of detector details.
            detector_id: The ID of the detector.

        Returns:
            Detector data model.

        """
        return Detector(raw_data, detector_id=detector_id)

    @staticmethod
    def build_siemplify_findings_list_obj(raw_data: dict[str, Any], detector_id: str) -> list[Finding]:
        """Build list of Siemplify Finding objects from raw data.

        Args:
            raw_data: Raw JSON response containing 'Findings' key.
            detector_id: Detector ID.

        Returns:
            List of Finding objects.

        """
        return [
            AWSGuardDutyParser.build_siemplify_finding_obj(finding, detector_id)
            for finding in raw_data.get("Findings", [])
        ]
