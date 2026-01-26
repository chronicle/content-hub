# Copyright 2025 Google LLC
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

import abc
from typing import Generic, TypeVar

from ...types import ApiParams
from .session import AuthenticatedSession


class Apiable(abc.ABC, Generic[ApiParams]):
    """Interface for classes that manage API calls to external services."""

    @abc.abstractmethod
    def __init__(
        self,
        authenticated_session: AuthenticatedSession,
        configuration: ApiParams,
    ) -> None:
        self.session: AuthenticatedSession = authenticated_session
        self.configuration: ApiParams = configuration


ApiClient = TypeVar("ApiClient", bound=Apiable)
