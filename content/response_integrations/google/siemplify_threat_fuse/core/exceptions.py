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
class ThreatFuseStatusCodeException(Exception):
    """
    Status Code exception for Siemplify ThreatFuse
    """

    pass


class ThreatFuseValidationException(Exception):
    """
    Validation exception for Siemplify ThreatFuse
    """

    pass


class ThreatFuseNotFoundException(Exception):
    """
    Not Found exception for Siemplify ThreatFuse
    """

    pass


class ThreatFuseIndicatorsNotFoundException(Exception):
    """
    Indicators not found exception for Siemplify ThreatFuse
    """

    pass


class ThreatFuseInvalidCredentialsException(Exception):
    """
    Invalid Credentials exception for Siemplify ThreatFuse
    """

    pass


class ThreatFuseBadRequestException(Exception):
    """
    Bad Request exception for Siemplify ThreatFuse
    """

    pass
