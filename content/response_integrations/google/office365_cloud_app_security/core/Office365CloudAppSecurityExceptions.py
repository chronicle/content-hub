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
class Office365CloudAppSecurityError(Exception):
    """
    General exception for Office 365 Cloud App Security
    """

    pass


class Office365CloudAppSecurityAlreadyExistingError(Office365CloudAppSecurityError):
    """
    Exception for already existing case
    """

    pass


class Office365CloudAppSecurityNotFoundError(Office365CloudAppSecurityError):
    """
    Exception for not found case
    """

    pass


class Office365CloudAppSecurityLastItemError(Office365CloudAppSecurityError):
    """
    Exception for last item
    """

    pass
