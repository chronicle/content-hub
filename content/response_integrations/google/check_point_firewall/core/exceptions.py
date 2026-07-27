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
class CheckpointException(Exception):
    """
    CheckPointFirewall Exception
    """

    pass


class CheckpointManagerError(CheckpointException):
    """
    CheckPointFirewall Manager Exception
    """

    pass


class CheckpointManagerBadRequestException(CheckpointManagerError):
    """
    CheckPointFirewall Logs request 400 status code Exception
    """

    pass


class CheckpointManagerNotFoundException(CheckpointManagerError):
    """
    CheckPointFirewall Logs request 404 status code Exception
    """

    pass


class InvalidGroupException(CheckpointManagerError):
    """
    Invalid group exception
    """

    pass
