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

"""User-defined exceptions for the AkeylessSecurity integration."""

from __future__ import annotations


class AkeylessSecurityError(Exception):
    """Top-level base exception for all AkeylessSecurity integration errors."""


class InvalidConfigurationError(AkeylessSecurityError):
    """Raised when integration configuration parameters are invalid or missing."""


class ConnectivityError(AkeylessSecurityError):
    """Raised when a connectivity check against the AkeylessSecurity API fails."""


class SecretAccessError(AkeylessSecurityError):
    """Raised when fetching a secret version from AkeylessSecurity fails."""


class ParameterUpdateError(AkeylessSecurityError):
    """Raised when updating a parameter on an integration instance or connector fails."""


class JobFetchError(AkeylessSecurityError):
    """Raised when fetching job details from the SOAR platform fails."""


class JobSaveError(AkeylessSecurityError):
    """Raised when persisting an updated job back to the SOAR platform fails."""


class IntegrationCredentialSyncError(AkeylessSecurityError):
    """Raised when one or more errors occur during credential synchronization."""
