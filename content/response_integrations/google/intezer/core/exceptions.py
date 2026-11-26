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
class IntezerManagerError(Exception):
    """General Exception for Intezer manager"""


class IntezerAPILimitError(IntezerManagerError):
    """API Limit Exception for Intezer manager"""


class IntezerBadRequestError(IntezerManagerError):
    """Exception for Bad Request"""


class IntezerUserInputError(IntezerManagerError):
    """When requested entity is not found in Intezer"""


class IntezerNotFoundError(IntezerUserInputError):
    """When requested entity is not found in Intezer"""


class IntezerInvalidFormat(IntezerManagerError):
    """When requested entity is not valid in Intezer"""


class IntezerTimeoutException(IntezerManagerError):
    """When there is timeout in Intezer"""


class IntezerUnexpectedStatusException(IntezerManagerError):
    """When there is an unexpected analysis status in Intezer"""
