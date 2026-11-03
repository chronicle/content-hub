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
class MandiantDTMException(Exception):
    """General exception for Mandiant DTM"""


class MandiantDTMManagerException(MandiantDTMException):
    """Exception for Mandiant DTM manager"""


class MandiantDTMBadRequestException(MandiantDTMException):
    """Exception for Bad Request"""


class MandiantDTMInvalidParameters(MandiantDTMException):
    """Exception in case of integration parameters not provided"""


class MandiantDTMInvalidUnicodeKeyError(MandiantDTMException):
    """Exception raised when a key contains Unicode characters."""
