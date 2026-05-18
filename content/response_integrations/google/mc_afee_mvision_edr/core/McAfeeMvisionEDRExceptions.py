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
class McAfeeMvisionEDRException(Exception):
    """
    Common McAfee Mvision EDR Exception
    """

    pass


class CaseNotFoundException(McAfeeMvisionEDRException):
    """
    Exception if case not found in McAfee Mvision EDR
    """

    pass


class TaskFailedException(McAfeeMvisionEDRException):
    """
    Exception if task failed in McAfee Mvision EDR
    """

    pass


class UnknownTaskStatusException(McAfeeMvisionEDRException):
    """
    Exception if Task status unknown for Siemplify
    """

    pass
