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

"""ThreatConnect V3 custom exceptions."""

from __future__ import annotations


class ThreatConnectError(Exception):
    """Generic exception for ThreatConnect integration."""


class InvalidRequestParametersError(ThreatConnectError):
    """Exception raised when request parameters are invalid."""


class ThreatConnectHTTPError(ThreatConnectError):
    """Exception raised when an HTTP error occurs."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class ThreatConnectFileError(ThreatConnectError):
    """Exception raised when a file error occurs."""


class ThreatConnectInvalidJsonError(ThreatConnectError):
    """Exception raised when provided JSON is invalid."""
