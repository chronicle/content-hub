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
class GoogleCloudApiException(Exception):
    """General exception for Google Cloud API."""


class GoogleCloudApiAuthException(GoogleCloudApiException):
    """Exception in case of authentication error."""


class GoogleCloudApiInvalidJsonException(GoogleCloudApiException):
    """Exception in case of invalid JSON string provided."""


class GoogleCloudApiCertificateException(GoogleCloudApiException):
    """Exception in case of certificate error."""


class GoogleCloudApiHTTPException(GoogleCloudApiException):
    """Exception in case of HTTP error."""

    def __init__(self, message, status_code=None):
        super().__init__(message)
        self.status_code = status_code


class GoogleCloudApiFileException(GoogleCloudApiException):
    """Exception in case of file related error."""
