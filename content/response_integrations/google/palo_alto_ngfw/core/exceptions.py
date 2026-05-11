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
class NGFWException(Exception):
    """Exception raised for general Palo Alto NGFW errors."""


class GroupNotExistsException(Exception):
    """Exception raised when a specified group does not exist on the Palo Alto NGFW."""


class AlreadyExistsException(Exception):
    """Exception raised when an entity already exists on the Palo Alto NGFW."""


class CategoryNotExistsException(Exception):
    """
    Exception raised when a specified category does not exist on the Palo Alto NGFW.
    """
