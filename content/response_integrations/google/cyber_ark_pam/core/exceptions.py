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

"""Exceptions for CyberArk PAM."""

from __future__ import annotations


class CyberArkPamError(Exception):
    """Top-level base exception for all CyberArk PAM integration errors."""


class CyberArkPamManagerError(CyberArkPamError):
    """General Exception for CyberArk PAM manager."""


class CyberArkPamNotFoundError(CyberArkPamManagerError):
    """Not Found Exception for CyberArk PAM manager."""


class CyberArkPamAccountNotManagedError(CyberArkPamManagerError):
    """Account Not Managed Exception for CyberArk PAM manager."""


class CyberArkPamSyncJobError(CyberArkPamError):
    """Base exception for the CyberArk PAM sync credential job."""


class InvalidConfigurationError(CyberArkPamSyncJobError):
    """Raised when the job configuration or mapping is invalid."""


class SecretAccessError(CyberArkPamSyncJobError):
    """Raised when fetching password from CyberArk PAM fails."""


class ParameterUpdateError(CyberArkPamSyncJobError):
    """Raised when setting configuration parameter in SOAR fails."""


class JobFetchError(CyberArkPamSyncJobError):
    """Raised when fetching job details from SOAR fails."""


class JobSaveError(CyberArkPamSyncJobError):
    """Raised when saving updated job back to SOAR fails."""


class IntegrationCredentialSyncError(CyberArkPamSyncJobError):
    """Raised when one or more credentials fail to sync during the job."""
