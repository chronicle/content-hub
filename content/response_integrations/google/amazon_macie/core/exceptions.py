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
class AmazonMacieStatusCodeException(Exception):
    """
    Status Code exception from Amazon Macie manager
    """

    pass


class AmazonMacieValidationException(Exception):
    """
    Validation Exception for Amazon Macie manager
    """

    pass


class AmazonMacieResourceAlreadyExistsException(Exception):
    """
    Resource already exists Exception for Amazon Macie manager
    """

    pass


class AmazonMacieNotFoundException(Exception):
    """
    Not Found Exception for Amazon Macie manager
    """

    pass
