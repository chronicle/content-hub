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

"""Google Chronicle exceptions."""
from __future__ import annotations
INVALID_API_ROOT_ERROR = (
    "API Root should not contain 'backstory'. Please use the 1Platform API root."
)
INVALID_CREDENTIALS_ERROR = "Unable to parse credentials as JSON. Please validate creds"
API_LIMIT_ERROR_MESSAGE = "Reached API request limitation"
UNABLE_TO_CONNECT_ERROR = (
    "Unable to connect to Google Chronicle, please validate your credentials: %s"
)


class ChronicleInvestigationManagerError(Exception):
    """General Exception for Google Chronicle manager."""


class GoogleChronicleAPILimitError(Exception):
    """API Limit Exception for Google Chronicle manager."""


class TriageError(ChronicleInvestigationManagerError):
    """Exception for Triage action."""
