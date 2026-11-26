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
class GoogleCloudIAMManagerError(Exception):
    """
    General Exception for Google Cloud IAM manager
    """

    pass


class GoogleCloudIAMPolicyJSONError(Exception):
    """
    Google Cloud IAM Policy JSON Error
    """

    pass


class GoogleCloudIAMRoleJSONError(Exception):
    """
    Google Cloud IAM Role JSON Error
    """

    pass


class GoogleCloudIAMRoleExistsError(Exception):
    """
    Google Cloud IAM Role Exists Error
    """

    pass


class GoogleCloudIAMRoleMissingError(Exception):
    """
    Google Cloud IAM Role Missing Error
    """

    pass


class GoogleCloudIAMValidationError(Exception):
    """
    Google Cloud IAM Validation Error
    """

    pass


class GoogleCloudIAMServiceAccountExistsError(Exception):
    """
    Google Cloud IAM Service Account Error
    """

    pass


class GoogleCloudIAMRoleIDInvalidError(Exception):
    """
    Google Cloud IAM Role ID Invalid Error
    """

    pass


class GoogleCloudIAMServiceAccountNotFoundError(Exception):
    """
    Google Cloud IAM Role ID Invalid Error
    """
