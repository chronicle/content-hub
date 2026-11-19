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


class GoogleThreatIntelligenceExceptions(Exception):
    """General exception for Google Threat Intelligence."""


class GoogleThreatIntelligenceAuthException(GoogleThreatIntelligenceExceptions):
    """Exception in case of authentication error."""


class GoogleThreatIntelligenceHTTPException(GoogleThreatIntelligenceExceptions):
    """Exception in case of HTTP error."""

    def __init__(self, message, status_code=None):
        super().__init__(message)
        self.status_code = status_code


class GoogleThreatIntelligenceTransientException(GoogleThreatIntelligenceHTTPException):
    """Exception in case of transient HTTP error."""


class ProjectNotFoundError(Exception):
    """Exception in case of specified project is not found"""


class GoogleThreatIntelligenceBadRequestException(GoogleThreatIntelligenceExceptions):
    """Exception in case of bad request error."""


class GoogleThreatIntelligencePermissionException(GoogleThreatIntelligenceExceptions):
    """Exception in case of permission error."""


class GoogleThreatIntelligenceNotFoundException(GoogleThreatIntelligenceExceptions):
    """Exception in case of not found error."""


class FileOverwriteException(GoogleThreatIntelligenceExceptions):
    """Exception in case of overwriting existing file"""


class PathNotExistException(GoogleThreatIntelligenceExceptions):
    """Exception in case of path does not exist"""


class FileSubmissionError(GoogleThreatIntelligenceExceptions):
    """Raised when an error occurs while sending a file for submission"""


class ZipExtractionError(GoogleThreatIntelligenceExceptions):
    """Raised when an error occurs when open zip file"""


class EntityNotFoundOrEmptyResults(GoogleThreatIntelligenceExceptions):
    """Raised when an entity was not found or empty result returned with external API"""


class ParamsValidationException(GoogleThreatIntelligenceExceptions):
    """Raised when action input parameter validation fails"""
