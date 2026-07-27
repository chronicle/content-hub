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
class CybereasonError(Exception):
    pass


class CybereasonManagerError(CybereasonError):
    pass


class CybereasonManagerNotFoundError(CybereasonError):
    pass


class CybereasonTimeoutError(CybereasonError):
    pass


class CybereasonManagerIsolationError(CybereasonError):
    def __init__(self, message, status="Unknown error"):
        super(CybereasonManagerIsolationError, self).__init__(message)
        self.status = status


class CybereasonNotFoundError(CybereasonError):
    pass


class CybereasonSuccessWithFailureError(CybereasonError):
    pass


class CybereasonClientError(CybereasonError):
    pass


class CybereasonInvalidQueryError(CybereasonError):
    pass


class CybereasonInvalidFormatError(CybereasonError):
    pass


class CybereasonMalopProcessError(CybereasonError):
    """Malop processes/files not found in malop ID API response."""


class CybereasonUniqueIdError(CybereasonError):
    """Action Param "Values" processes/files not found in Malop API response."""


class CybereasonCertificateError(CybereasonError):
    """Raise if Cybereason certificate is not validated."""
