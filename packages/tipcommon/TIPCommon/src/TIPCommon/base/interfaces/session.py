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


_R = TypeVar("_R")


class Session(abc.ABC, Generic[_R]):
    """Interface that defines a session object that must provide an API session
    functionality.

    Use this interface to type values that might use different types of sessions, or
    would be mocked with a different implementation of a session like requests or httpx.

    Attributes:
        - headers
        - verify

    Methods:
        - post()
        - get()
        - delete()
        - patch()
        - put()
    """
    headers: dict
    verify: bool

    @abc.abstractmethod
    def post(self, url: str, *args, **kwargs) -> _R:
        pass

    @abc.abstractmethod
    def get(self, url: str, *args, **kwargs) -> _R:
        pass

    @abc.abstractmethod
    def delete(self, url: str, *args, **kwargs) -> _R:
        pass

    @abc.abstractmethod
    def patch(self, url: str, *args, **kwargs) -> _R:
        pass

    @abc.abstractmethod
    def put(self, url: str, *args, **kwargs) -> _R:
        pass

    @abc.abstractmethod
    def request(self, method: str, url: str, *args, **kwargs) -> _R:
        pass


AuthenticatedSession = TypeVar("AuthenticatedSession", bound=Session)
