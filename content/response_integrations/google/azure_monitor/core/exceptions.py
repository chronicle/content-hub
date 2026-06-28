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
class AzureMonitorError(Exception):
    """General exception for Azure Monitor."""


class AzureMonitorErrorInvalidParameterError(AzureMonitorError):
    """Invalid Parameter error."""


class AzureMonitorHTTPError(AzureMonitorError):
    """Exception in case of HTTP error."""

    def __init__(self, message, *args, status_code=None) -> None:
        super().__init__(message, *args)
        self.status_code = status_code


class InvalidRequestParametersError(AzureMonitorError):
    """Invalid HTTP Requests Parameters Error."""


class InvalidCredsError(AzureMonitorError):
    """Invalid Credentials Error."""
