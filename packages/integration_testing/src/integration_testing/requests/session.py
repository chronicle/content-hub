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
from collections import OrderedDict
from typing import TYPE_CHECKING, Any, Generic, TypeVar

import requests
from TIPCommon.base.interfaces import Session
from TIPCommon.base.utils import is_native, nativemethod

from integration_testing.custom_types import NO_RESPONSE, Product, Request, RouteFunction, UrlPath
from integration_testing.request import HttpMethod, MockRequest

from .response import MockResponse

if TYPE_CHECKING:
    from collections.abc import Iterable, MutableMapping

    from TIPCommon.types import SingleJson


Response = TypeVar("Response", bound=MockResponse)
Routes = dict[str, dict[UrlPath, RouteFunction[Response]]]


@dataclasses.dataclass(slots=True, frozen=True)
class HistoryRecord(Generic[Request, Response]):
    request: Request
    response: Response


class MockSession(requests.Session, Session[Response], Generic[Request, Response, Product]):
    def __init__(self, mock_product: Product | None = None) -> None:
        """Initialize the session."""
        super().__init__()
        self.verify: bool = True
        self.headers: SingleJson = {}
        self.adapters: OrderedDict = OrderedDict()
        self.stream: bool = False
        self.request_history: list[HistoryRecord] = []
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
    def get_routed_functions(self) -> Iterable[RouteFunction[Response]]:
        """Get the routed functions."""
        raise NotImplementedError

    def clear_record(self) -> None:
        """Clear the request history."""
        self.request_history.clear()

    def request(self, method: str, url: str, *args: Any, **kwargs: Any) -> Response:  # noqa: ANN401
        """Mock a general request method."""
        parsed_url: urllib.parse.ParseResult = urllib.parse.urlparse(url)
        request: MockRequest = MockRequest(
            method=HttpMethod(method),
            url=parsed_url,
            headers=self.headers,
            args=args,
            kwargs=kwargs,
        )
        response: MockResponse = self._do_request(method, request)
        response.request = request

        history_record: HistoryRecord = HistoryRecord(request, response)
        self.request_history.append(history_record)

        return response

    def get(self, url: str, *args: Any, **kwargs: Any) -> Response:  # noqa: ANN401
        """Mock a GET request."""
        return self.request(HttpMethod.GET.value, url, *args, **kwargs)

    def delete(self, url: str, *args: Any, **kwargs: Any) -> Response:  # noqa: ANN401
        """Mock a DELETE request."""
        return self.request(HttpMethod.DELETE.value, url, *args, **kwargs)

    def post(self, url: str, *args: Any, **kwargs: Any) -> Response:  # noqa: ANN401
        """Mock a POST request."""
        return self.request(HttpMethod.POST.value, url, *args, **kwargs)

    def put(self, url: str, *args: Any, **kwargs: Any) -> Response:  # noqa: ANN401
        """Mock a PUT request."""
        return self.request(HttpMethod.PUT.value, url, *args, **kwargs)

    def patch(self, url: str, *args: Any, **kwargs: Any) -> Response:  # noqa: ANN401
        """Mock a PATCH request."""
        return self.request(HttpMethod.PATCH.value, url, *args, **kwargs)

    def _do_request(self, method: str, request: Request) -> Response:
        response: Response = NO_RESPONSE
        path: str = request.url.path
        for path_pattern, fn in self.routes[method].items():
            if re.fullmatch(path_pattern, path) is not None:
                response = fn(request)
                break

        self._validate_response(response, method, path)
        return response

    def _validate_response(
        self,
        response: Response,
        method: str,
        path: str,
    ) -> None:
        msg: str
        if response is None or response is NotImplemented:
            msg = (
                "Null or UnImplemented Response!"
                f" Request with method '{method}' to URL '{path}'"
                f" returned {response!r} instead of a response object."
                " Perhaps you forgot to return a response object in the correlating"
                " router."
            )
            raise RuntimeError(msg)

        if response is NO_RESPONSE:
            msg = (
                f"path '{path}' doesn't match with any of the other '{method}' "
                f"routes patterns: {list(self.routes[method].keys())}"
            )
            raise ValueError(msg)

    def _set_routes(self) -> None:
        functions: Iterable[RouteFunction[Response]] = self.get_routed_functions()
        for function in functions:
            if not hasattr(function, "__routes__"):
                msg: str = f"Function '{function.__name__}' has no routes"
                raise ValueError(msg)

            routes: MutableMapping[str, set[UrlPath]] = function.__routes__
            for method, paths in routes.items():
                for path in paths:
                    self.routes[method][path] = function
