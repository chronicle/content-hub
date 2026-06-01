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
from .PanoramaExceptions import PanoramaSeverityException
from .PanoramaConstants import PANORAMA_TO_SIEM_SEVERITY
from .PanoramaCommon import PanoramaCommon


class PanoramaValidator:
    @staticmethod
    def validate_severity(severity):
        # type: (str or unicode) -> None or PanoramaSeverityException
        """
        Validate if severity is acceptable
        @param severity: Severity. Ex. Low
        """
        acceptable_severities = [
            key.lower() for key in list(PANORAMA_TO_SIEM_SEVERITY.keys())
        ]
        if severity not in acceptable_severities:
            raise PanoramaSeverityException(
                f'Severity "{severity}" is not in {PanoramaCommon.convert_list_to_comma_separated_string(acceptable_severities)}'
            )
