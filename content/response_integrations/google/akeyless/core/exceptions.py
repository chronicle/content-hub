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

"""User-defined exceptions for the Akeyless integration."""

from __future__ import annotations


class AkeylessError(Exception):
    """Top-level base exception for all Akeyless integration errors."""


class InvalidConfigurationError(AkeylessError):
    """Raised when integration configuration parameters are invalid or missing."""


class ConnectivityError(AkeylessError):
    """Raised when a connectivity check against the Akeyless API fails."""


class SecretAccessError(AkeylessError):
    """Raised when fetching a secret version from Akeyless fails."""


class ParameterUpdateError(AkeylessError):
    """Raised when updating a parameter on an integration instance or connector fails."""


class JobFetchError(AkeylessError):
    """Raised when fetching job details from the SOAR platform fails."""


class JobSaveError(AkeylessError):
    """Raised when persisting an updated job back to the SOAR platform fails."""
