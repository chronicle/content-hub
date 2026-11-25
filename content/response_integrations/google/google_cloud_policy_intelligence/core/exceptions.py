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
class GoogleCloudPolicyIntelligenceError(Exception):
    """General Exception for Google Cloud Policy Intelligence"""


class InsufficientResourcePermissionError(GoogleCloudPolicyIntelligenceError):
    """No permissions granted for Project Or Organization level"""


class ProjectNotFoundError(GoogleCloudPolicyIntelligenceError):
    """Project ID not found for requested API service"""


class MaximumRequestLimitError(GoogleCloudPolicyIntelligenceError):
    """Maximum requests sent in a given amount of time"""


class InvalidServiceAccountError(GoogleCloudPolicyIntelligenceError):
    """Service Account details are not correct"""
