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
class MicrosoftAzureSentinelError(Exception):
    pass


class TimeoutIsApproachingError(MicrosoftAzureSentinelError):
    pass


class MicrosoftAzureSentinelManagerError(MicrosoftAzureSentinelError):
    def __init__(self, *args, **kwargs):
        self.error_context = kwargs.get("error_context", {})
        super().__init__(*args)


class MicrosoftAzureSentinelPermissionError(MicrosoftAzureSentinelManagerError):
    pass


class MicrosoftAzureSentinelUnauthorizedError(MicrosoftAzureSentinelManagerError):
    pass


class MicrosoftAzureSentinelBadRequestError(MicrosoftAzureSentinelManagerError):
    pass


class MicrosoftAzureSentinelNotFoundError(MicrosoftAzureSentinelManagerError):
    pass


class MicrosoftAzureSentinelValidationError(MicrosoftAzureSentinelError):
    pass


class MicrosoftAzureSentinelTimeoutError(MicrosoftAzureSentinelError):
    pass


class MicrosoftAzureSentinelConflictError(MicrosoftAzureSentinelError):
    pass


class MicrosoftAzureSentinelServerError(MicrosoftAzureSentinelError):
    """Microsoft Azure Sentinel Server Error."""


class InvalidParameterError(MicrosoftAzureSentinelError):
    """
    Exception in case of invalid parameter
    """

    pass


class MicrosoftAzureSentinelIncidentNotFoundError(MicrosoftAzureSentinelManagerError):
    """Exception in case of not found incident"""
