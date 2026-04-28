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
from .ObserveITExceptions import ObserveITSeverityException
from .ObserveITConstants import OBSERVE_IT_TO_SIEM_SEVERITY
from .ObserveITCommon import ObserveITCommon


class ObserveITValidator:
    @staticmethod
    def validate_severity(severity):
        # type: (str or unicode) -> None or ObserveITSeverityException
        """
        Validate if severity is acceptable
        @param severity: Severity. Ex. Low
        """
        acceptable_severities = list(OBSERVE_IT_TO_SIEM_SEVERITY.keys())
        if severity not in acceptable_severities:
            raise ObserveITSeverityException(
                f'Severity "{severity}" is not in {ObserveITCommon.convert_list_to_comma_separated_string(acceptable_severities)}'
            )
