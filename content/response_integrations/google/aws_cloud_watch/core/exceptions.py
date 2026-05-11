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
class AWSCloudWatchStatusCodeException(Exception):
    """
    Status Code exception from AWS CloudWatch manager
    """

    pass


class AWSCloudWatchInvalidParameterException(Exception):
    """
    Invalid Parameter exception from AWS CloudWatch manager
    """

    pass


class AWSCloudWatchValidationException(Exception):
    """
    Validation exception from AWS CloudWatch manager
    """

    pass


class AWSCloudWatchResourceNotFoundException(Exception):
    """
    Resource Not Found exception from AWS CloudWatch manager
    """

    pass


class AWSCloudWatchLogGroupNotFoundException(Exception):
    """
    Log Group Not Found exception from AWS CloudWatch manager
    """

    pass


class AWSCloudWatchLogStreamNotFoundException(Exception):
    """
    Log Stream Not Found exception from AWS CloudWatch manager
    """

    pass
