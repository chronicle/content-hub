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
from soar_sdk.SiemplifyUtils import unix_now


class Microsoft365DefenderException(Exception):
    """
    General exception for Microsoft 365 Defender
    """

    pass


class TooManyRequestsError(Microsoft365DefenderException):
    def __init__(self, *args, **kwargs):
        self.encountered_at = unix_now()
        self.retry_after = kwargs.pop('retry_after', None)
        super().__init__(*args, **kwargs)


class NotFoundItemException(Microsoft365DefenderException):
    pass


class NotEnoughEntitiesException(Microsoft365DefenderException):
    pass


class APIPermissionError(Microsoft365DefenderException):
    pass


class MissingSeverityFieldError(Microsoft365DefenderException):
    pass


class Microsoft365DefenderNotImplementedException(Microsoft365DefenderException):
    pass


class Microsoft365DefenderServerError(Microsoft365DefenderException):
    """Exception raised when the Microsoft 365 Defender API returns a server error."""
