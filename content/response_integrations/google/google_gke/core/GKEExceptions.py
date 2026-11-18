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
class GoogleGKEValidationError(Exception):
    """
    General Exception for Google GKE validation errors.
    """


class GoogleGKEManagerError(Exception):
    """
    General Exception for Google Kubernetes Engine manager
    """


class GoogleCloudAuthenticationError(Exception):
    """
    General Exception for Google Cloud Authentication errors.
    """


class GoogleGKEServiceError(Exception):
    """
    General Exception for Google Kubernetes Engine service.
    """


class GoogleGKEManagerCriticalError(Exception):
    """
    Critical Exception for Google Kubernetes Engine manager
    """


class GoogleGKEProjectLookupError(GoogleGKEManagerCriticalError):
    """
    Project Lookup Exception for Google Kubernetes Engine manager
    """


class GoogleGKENotFoundError(GoogleGKEManagerError):
    """
    Not Found Exception for Google Kubernetes Engine manager
    """


class GoogleGKEInvalidRequestArgumentError(GoogleGKEManagerError):
    """
    Invalid Request Argument Exception for Google Kubernetes Engine manager
    """


class GoogleGKEInvalidZoneError(GoogleGKEInvalidRequestArgumentError):
    """
    Invalid Zone Exception for Google Kubernetes Engine manager
    """


class GoogleGKEInvalidClusterNameError(GoogleGKEInvalidRequestArgumentError):
    """
    Exception for Invalid Cluster Name for Google Kubernetes Engine manager
    """


class GoogleGKEInvalidNodePoolNameError(GoogleGKEInvalidRequestArgumentError):
    """
    Exception for Invalid Cluster Node Pool Name for Google Kubernetes Engine manager
    """


class GoogleGKEInvalidOperationNameError(GoogleGKEInvalidRequestArgumentError):
    """
    Exception for Invalid Operation Name for Google Kubernetes Engine manager
    """


class NegativeValueException(Exception):
    """
    Exception for negative value
    """


class NonPositiveValueException(Exception):
    """
    Exception for non positive value
    """


class InvalidJSONFormatException(Exception):
    """
    Exception for invalid JSON format
    """


class MissingParametersException(Exception):
    """
    Exception for missing parameters
    """
