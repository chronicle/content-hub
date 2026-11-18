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
class GSuiteManagerError(Exception):
    """General Exception for GSuite manager."""


class GSuiteValidationException(Exception):
    """Validate Exception for GSuite."""


class GSuiteParameterValidationError(Exception):
    """Validate Parameter Exception for GSuite."""


class GSuiteEntityExistsException(Exception):
    """Entity exists exception for GSuite."""


class GSuiteNotFoundException(Exception):
    """Not Found exception for GSuite."""


class GoogleCloudAuthenticationError(Exception):
    """General Exception for Google Cloud Authentication errors."""


class InvalidJSONFormatException(Exception):
    """Invalid JSON format error."""


class GSuiteAuthError(Exception):
    """Exception for general errors in GSuiteAuthManager."""
