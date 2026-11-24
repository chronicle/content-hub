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
class GoogleCloudComputeManagerError(Exception):
    """
    General Exception for Google Cloud Compute manager
    """


class GoogleCloudComputeAPILimitError(Exception):
    """
    API Limit Exception for Google Cloud Compute manager
    """


class GoogleCloudComputeResourceNameValidationError(Exception):
    """
    Resource Name Validation Exception for Google Cloud Compute manager
    """


class GoogleCloudComputeOperationError(Exception):
    """
    Operation Exception for Google Cloud Compute manager
    """


class GoogleCloudComputeValidationError(Exception):
    """
    Validation Exception for Google Cloud Compute manager
    """


class GoogleCloudComputeInvalidZone(Exception):
    """
    Invalid Zone Exception for Google Cloud Compute manager
    """


class GoogleCloudTransportException(Exception):
    """
    Transport Exception for Google Cloud Compute manager
    """


class GoogleCloudAuthenticationError(Exception):
    """
    Google Cloud Compute Authentication Error for Google Cloud Compute manager
    """


class GoogleCloudComputeInvalidInstanceID(Exception):
    """
    Google Cloud Compute Invalid Instance ID Error for Google Cloud Compute manager
    """


class GoogleCloudPolicyJSONError(Exception):
    """
    Google Cloud Compute Invalid IAM Policy JSON Error for Google Cloud Compute manager
    """


class GoogleCloudComputeLabelsValidationError(Exception):
    """
    Validation Exception for labels for Google Cloud Compute manager
    """


class GoogleCloudComputeTimeoutError(Exception):
    """
    Timeout Exception for Google Cloud Compute actions.
    """
