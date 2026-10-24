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

"""Custom exception classes for Atlassian Confluence Server."""
from __future__ import annotations


class ConfluenceManagerError(Exception):
    """General Exception for Confluence manager."""


class ConfluenceValidationError(Exception):
    """Validation Exception for Confluence Manager
    in case parameters not provided."""


class ConfluenceBadRequestError(Exception):
    """Bad Request Exception for HTTPError."""


class ConfluenceHTTPError(Exception):
    """HTTP Error for API request."""


class ConfluencePATAuthenticationError(Exception):
    """Exception when Personal access token is invalid."""


class ConfluenceInvalidLimitError(Exception):
    """Exception if invalid value is provided for limit param."""


class ConfluenceFilterKeyParamError(Exception):
    """Exception for filter_key param is empty."""
