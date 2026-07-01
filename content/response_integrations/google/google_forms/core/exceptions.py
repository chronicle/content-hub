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


class GoogleFormsManagerError(Exception):
    """General base exception for the Google Forms integration."""


class GoogleFormsValidationException(GoogleFormsManagerError):
    """Raised for data structure validation errors."""


class GoogleFormsAuthenticationError(GoogleFormsManagerError):
    """Raised for authentication-related errors."""


class InvalidJSONFormatException(GoogleFormsManagerError):
    """Raised for errors in parsing JSON responses."""


class InvalidParameterException(GoogleFormsManagerError):
    """Raised for invalid parameters provided to a method."""


class InvalidFormIdsException(GoogleFormsManagerError):
    """Raised for errors related to invalid form IDs."""
