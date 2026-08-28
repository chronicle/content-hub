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
class SplunkException(Exception):
    pass


class SplunkManagerException(SplunkException):
    pass


class SplunkHTTPException(SplunkManagerException):
    pass


class SplunkNotFoundException(SplunkHTTPException):
    pass


class UnableToUpdateNotableEvents(SplunkManagerException):
    pass


class UnableToLoadSourceEvents(SplunkManagerException):
    pass


class SplunkConnectorException(SplunkException):
    pass


class SplunkCaCertificateException(SplunkManagerException):
    pass


class MissingEntityKeysException(Exception):
    def __init__(self, missing_entity_keys):
        self.missing_entity_keys = missing_entity_keys
        super().__init__()


class SplunkBadRequestException(SplunkManagerException):
    pass


class AdhocSearchLevelException(SplunkManagerException):
    pass
