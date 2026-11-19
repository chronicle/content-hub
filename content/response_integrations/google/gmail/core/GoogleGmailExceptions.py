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
class InvalidJSONFormatException(Exception):
    """Invalid JSON format error."""


class GoogleCloudAuthenticationError(Exception):
    """General Exception for Google Cloud Authentication errors."""


class GoogleGmailValidationError(Exception):
    """General Exception for Google Gmail validation errors."""


class GoogleGmailManagerError(Exception):
    """General Exception for Google Gmail manager."""


class GoogleGmailServiceError(Exception):
    """General Exception for Google Gmail service."""


class GoogleGmailPermissionDeniedError(GoogleGmailManagerError):
    """Permission denied for Google Gmail manager."""


class GoogleGmailProjectLookupError(GoogleGmailPermissionDeniedError):
    """Project Lookup Exception for Google Gmail manager."""


class GoogleGmailNotFoundError(GoogleGmailManagerError):
    """Not Found Exception for Google Gmail manager."""


class GoogleGmailInvalidRequestArgumentError(GoogleGmailManagerError):
    """Invalid Request Argument Exception for Google Gmail manager."""


class GoogleGmailThrottlingOverloaded(GoogleGmailManagerError):
    """Throttling Exception for Google Gmail service."""
