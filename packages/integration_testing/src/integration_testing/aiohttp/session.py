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

import dataclasses
import re
import urllib.parse
from collections import UserList
from typing import TYPE_CHECKING, Any, Generic, SupportsIndex, TypeVar

import aiohttp
from TIPCommon.base.utils import is_native, nativemethod

from integration_testing.aiohttp.response import MockClientResponse
from integration_testing.custom_types import NO_RESPONSE, Product, Request, RouteFunction, UrlPath
from integration_testing.request import HttpMethod, MockRequest

if TYPE_CHECKING:
    from collections.abc import Iterable, MutableMapping

    from TIPCommon.types import SingleJson


Response = TypeVar("Response", bound=MockClientResponse)
Routes = dict[str, dict[UrlPath, RouteFunction]]


@dataclasses.dataclass(slots=True, frozen=True)
class HistoryRecord(Generic[Request, Response]):
    request: Request
    response: Response


class HistoryRecordsList(UserList[HistoryRecord[Request, Response]]):
    def __init__(self, *history_records: HistoryRecord) -> None:
        if not all(isinstance(el, HistoryRecord) for el in history_records):
            msg: str = "List items must be of type HistoryRecord"
            raise TypeError(msg)

        super().__init__(history_records)

    def __copy__(self) -> HistoryRecordsList:
        return HistoryRecordsList(*self)

    def __getitem__(
        self,
        item: int | slice | SupportsIndex,
    ) -> HistoryRecordsList | HistoryRecord:
        result: slice | HistoryRecordsList = super().__getitem__(item)
        if isinstance(item, slice):
            return HistoryRecordsList(*result)

        return result

    def assert_url_path_with_regex(
        self,
        regex_pattern: str,
        start: int = 0,
        stop: int = -1,
    ) -> None:
        """Assert that all history records path matches given regex."""
        if not all(re.search(regex_pattern, hr.request.url.path) for hr in self[start:stop]):
            msg: str = "Not all history records have the expected path regex."
            raise RuntimeError(msg)

    def assert_headers(self, headers: dict[str, str], start: int = 0, stop: int = -1) -> None:
        """Assert that all history records have specific headers set."""
        for key, value in headers.items():
            if not all(hr.request.headers.get(key) == value for hr in self[start:stop]):
                msg: str = "Not all history records have the expected headers set."
                raise RuntimeError(msg)


class MockClientSession(aiohttp.ClientSession, Generic[Request, Response, Product]):
    def __init__(
        self,
        *args: Any,  # noqa: ANN401
        mock_product: Product | None = None,
        **kwargs: Any,  # noqa: ANN401
    ) -> None:
        super().__init__(*args, **kwargs)
        self._default_headers: SingleJson = {}
        self.request_history: HistoryRecordsList[HistoryRecord] = HistoryRecordsList()
        self.routes: Routes = {
            HttpMethod.GET.value: {},
            HttpMethod.DELETE.value: {},
            HttpMethod.POST.value: {},
            HttpMethod.PUT.value: {},
            HttpMethod.PATCH.value: {},
        }

        self._product: Product | None = mock_product

        if not is_native(self.get_routed_functions):
            self._set_routes()

    @nativemethod
    def get_routed_functions(self) -> Iterable[RouteFunction]:
        raise NotImplementedError

    def clear_record(self) -> None:
        self.request_history.clear()

    async def request(
        self,
        method: str,
        url: str,
        *args: Any,  # noqa: ANN401
        **kwargs: Any,  # noqa: ANN401
    ) -> Response:
        """Mock a general request method."""
        parsed_url: urllib.parse.ParseResult = urllib.parse.urlparse(url)
        request: MockRequest = MockRequest(
            method=HttpMethod(method),
            url=parsed_url,
            headers=self.headers,
            args=args,
            kwargs=kwargs,
        )
        response: MockClientResponse = await self._do_request(method, request)
        response.request = request

        history_record: HistoryRecord = HistoryRecord(request, response)
        self.request_history.append(history_record)

        return response

    async def get(self, url: str, *args: Any, **kwargs: Any) -> Response:  # noqa: ANN401
        return await self.request(HttpMethod.GET.value, url, *args, **kwargs)

    async def delete(self, url: str, *args: Any, **kwargs: Any) -> Response:  # noqa: ANN401
        return await self.request(HttpMethod.DELETE.value, url, *args, **kwargs)

    async def post(self, url: str, *args: Any, **kwargs: Any) -> Response:  # noqa: ANN401
        return await self.request(HttpMethod.POST.value, url, *args, **kwargs)

    async def put(self, url: str, *args: Any, **kwargs: Any) -> Response:  # noqa: ANN401
        return await self.request(HttpMethod.PUT.value, url, *args, **kwargs)

    async def patch(self, url: str, *args: Any, **kwargs: Any) -> Response:  # noqa: ANN401
        return await self.request(HttpMethod.PATCH.value, url, *args, **kwargs)

    async def _do_request(self, method: str, request: Request) -> Response:
        response: Response = NO_RESPONSE
        path: str = request.url.path
        for path_pattern, fn in self.routes[method].items():
            if re.search(path_pattern, path) is not None:
                response = fn(request)
                response._request_info = request  # noqa: SLF001
                break

        self._validate_response(response, method, path)
        return response

    def _validate_response(self, response: Response, method: str, path: str) -> None:
        msg: str
        if response is None:
            msg = (
                f"Null Response! Request with method '{method}' to URL '{path}' "
                "returned None instead of a response object. Perhaps you forgot "
                "to return a response object in the correlating router."
            )
            raise RuntimeError(msg)

        if response is NO_RESPONSE:
            msg = (
                f"path '{path}' doesn't match with any of the other '{method}' "
                f"routes patterns: {list(self.routes[method].keys())}"
            )
            raise ValueError(msg)

    def _set_routes(self) -> None:
        functions: Iterable[RouteFunction] = self.get_routed_functions()
        for function in functions:
            if not hasattr(function, "__routes__"):
                msg: str = f"Function '{function.__name__}' has no routes"
                raise ValueError(msg)

            routes: MutableMapping[str, list[UrlPath]] = function.__routes__
            for method, paths in routes.items():
                for path in paths:
                    self.routes[method][path] = function
