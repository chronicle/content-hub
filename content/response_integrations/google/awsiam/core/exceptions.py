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

"""AWS IAM integration exceptions and errors"""
from __future__ import annotations


class AWSIAMError(Exception):
    """General purpose base exception for AWS IAM"""


class AWSIAMStatusCodeException(AWSIAMError):
    """Status Code exception from AWS IAM manager"""


class AWSIAMValidationException(AWSIAMError):
    """Validation exception from AWS IAM manager"""


class AWSIAMEntityAlreadyExistsException(AWSIAMError):
    """Entity Already Exists exception from AWS IAM manager"""


class AWSIAMLimitExceededException(AWSIAMError):
    """Limit exceeded exception for AWS IAM manager"""


class AWSIAMEntityNotFoundException(AWSIAMError):
    """Not found exception for AWS IAM manager"""


class AWSIAMMalformedPolicyDocument(AWSIAMError):
    """Malformed policy document exception for AWS IAM manager"""


class AWSIAMInvalidInputException(AWSIAMError):
    """Invalid Input exception for AWS IAM manager"""
