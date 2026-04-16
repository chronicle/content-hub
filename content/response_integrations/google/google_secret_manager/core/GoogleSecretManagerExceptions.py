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

"""User-defined exceptions for the Google Secret Manager integration."""

from __future__ import annotations


class GoogleSecretManagerError(Exception):
    """Top-level base exception for all Google Secret Manager integration errors."""


class InvalidConfigurationError(GoogleSecretManagerError):
    """Raised when integration configuration parameters are invalid or missing.

    Examples:
        - Malformed Service Account JSON.
        - Missing or unresolvable Project ID.
        - Invalid Credential Mapping JSON supplied to the sync job.
    """


class ConnectivityError(GoogleSecretManagerError):
    """Raised when a connectivity check against the Secret Manager API fails."""


class SecretAccessError(GoogleSecretManagerError):
    """Raised when fetching a secret version from Secret Manager fails."""


class ParameterUpdateError(GoogleSecretManagerError):
    """Raised when updating a parameter on an integration instance or connector fails."""


class JobFetchError(GoogleSecretManagerError):
    """Raised when fetching job details from the SOAR platform fails."""


class JobSaveError(GoogleSecretManagerError):
    """Raised when persisting an updated job back to the SOAR platform fails."""
