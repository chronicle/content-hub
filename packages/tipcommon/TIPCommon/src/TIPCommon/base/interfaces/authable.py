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

from __future__ import annotations

import abc
from typing import Generic, TypeVar

from ...types import AuthParams
from ..utils import CreateSession
from .session import AuthenticatedSession


class Authable(abc.ABC, Generic[AuthParams]):
    """Interface for classes that manage authentication with external services."""

    def __init__(self) -> None:
        self.session: AuthenticatedSession = CreateSession.create_session()

    @abc.abstractmethod
    def authenticate_session(self, params: AuthParams) -> None:
        """Authenticate the `self.session` attribute of the class using `params`.

        This will let the user create an object using some session, and with this method
        they can authenticate with the service this session will request

        Args:
            params:
                Authentication parameters. Can be an object, dataclass, TypedDict,
                namedtuple or anything that holds all the authentication parameters.

        """


Authenticator = TypeVar("Authenticator", bound=Authable)
