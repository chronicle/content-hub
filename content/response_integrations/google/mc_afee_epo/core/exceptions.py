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
class McAfeeEpoException(Exception):
    pass


class McAfeeEpoManagerException(McAfeeEpoException):
    pass


class McAfeeInvalidParamException(McAfeeEpoException):
    pass


class McAfeeEpoCertificateException(McAfeeEpoManagerException):
    pass


class McAfeeEpoInvalidGroupException(McAfeeEpoManagerException):
    pass


class McAfeeEpoUnauthorizedException(McAfeeEpoManagerException):
    pass


class McAfeeEpoPermissionException(McAfeeEpoManagerException):
    pass


class McAfeeEpoBadRequestException(McAfeeEpoManagerException):
    pass


class McAfeeEpoNotFoundException(McAfeeEpoManagerException):
    pass


class McAfeeEpoTaskNotFoundException(McAfeeEpoManagerException):
    pass


class McAfeeEpoMissingEntityException(McAfeeEpoException):
    pass
