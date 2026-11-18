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
class GoogleCloudArmorError(Exception):
    """Exceptions for Google Cloud Armor"""


class GoogleCloudArmorInvalidJsonError(Exception):
    """Exception in case of Invalid JSON"""


class GoogleCloudArmorStatusNotFoundError(GoogleCloudArmorError):
    """Exception in case of requested response not found."""


class GoogleCloudArmorValidationError(GoogleCloudArmorError):
    """Exception in case of invalid data provided."""


class GoogleCloudArmorPermissionsDeniedError(GoogleCloudArmorError):
    """Exception in case of permissions denied on your request."""


class GoogleCloudArmorRetryExceededError(GoogleCloudArmorError):
    """Exception in case of permissions denied on your request."""


class GoogleCloudArmorPolicyNotFoundError(GoogleCloudArmorError):
    """Exception in case of security policy not found."""


class GoogleCloudArmorInvalidRegionError(GoogleCloudArmorError):
    """Exception in case of region is invalid."""
