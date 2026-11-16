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


class AzureApiError(Exception):
    """General exception for Azure API."""


class AzureApiInvalidParameterError(AzureApiError):
    """Invalid Parameter error."""


class AzureApiHTTPError(AzureApiError):
    """Exception in case of HTTP error."""

    def __init__(self, message, *args, status_code=None) -> None:
        super().__init__(message, *args)
        self.status_code = status_code


class InvalidRequestParametersError(AzureApiError):
    """Invalid HTTP Requests Parameters Error."""


class InvalidCredsError(AzureApiError):
    """Invalid Credentials Error."""


class AzureApiInvalidJsonError(AzureApiError):
    """Invalid JSON exception."""


class AzureApiFileError(AzureApiError):
    """File exception."""


class AzureApiJobNotSupportedError(AzureApiError):
    """Job not supported exception."""
