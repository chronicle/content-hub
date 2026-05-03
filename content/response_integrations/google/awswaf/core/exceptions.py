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
class AWSWAFStatusCodeException(Exception):
    """
    Status Code exception from AWS WAF manager
    """

    pass


class AWSWAFValidationException(Exception):
    """
    Validation Exception for AWS WAF manager
    """

    pass


class AWSWAFCriticalValidationException(Exception):
    """
    Validation Exception for AWS WAF manager that should stop a playbook
    """

    pass


class AWSWAFNotFoundException(Exception):
    """
    Not Found Exception for AWS WAF manager
    """

    pass


class AWSWAFCriticalFNotFoundException(Exception):
    """
    Not Found Exception for AWS WAF manager that should stop a playbook
    """

    pass


class AWSWAFDuplicateItemException(Exception):
    """
    Duplicate Item Exception for AWS WAF Manager
    """

    pass


class AWSWAFLimitExceededException(Exception):
    """
    Resource Limit Exceeded for AWS WAF Manager
    """

    pass


class AWSWAFWebACLNotFoundException(Exception):
    """
    Web ACL Not Found Exception for AWS WAF
    """

    pass
