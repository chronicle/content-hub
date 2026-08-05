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
class ArcsightError(Exception):
    """
    General Arcsight exception
    """

    pass


class ArcsightInvalidParamError(ArcsightError):
    """
    General Exception for arcsight invalid input param's exception
    """

    pass


class ArcsightLoginError(ArcsightError):
    """
    General Exception for arcsight login failure
    """

    pass


class ColumnNotFoundException(ArcsightError):
    pass


class ArcsightApiError(ArcsightError):
    """
    General Exception for arcsight api manager
    """

    pass


class UnableToParseException(ArcsightError):
    """
    Exception if unable to parse value
    """

    def __init__(self, key, value):
        self.key = key
        self.value = value


class ArcsightNoEntitiesFoundError(ArcsightError):
    """
    General Exception for arcsight no entities were found
    """

    pass
