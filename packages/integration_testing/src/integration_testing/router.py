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

import collections
from typing import TYPE_CHECKING

from .request import HttpMethod

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable, MutableMapping

    from .custom_types import RouteFunction, UrlPath


def add_routes(
    routes: MutableMapping[HttpMethod, Iterable[UrlPath]],
) -> Callable[[RouteFunction], RouteFunction]:
    """Add routes to a function."""

    def wrapper(fn: RouteFunction) -> RouteFunction:
        _add_routes(routes, fn)
        return fn

    return wrapper


def get(path: UrlPath) -> Callable[[RouteFunction], RouteFunction]:
    """Add a GET route to a function."""

    def wrapper(fn: RouteFunction) -> RouteFunction:
        routes: dict[HttpMethod, Iterable[UrlPath]] = {HttpMethod.GET: (path,)}
        _add_routes(routes, fn)
        return fn

    return wrapper


def delete(path: UrlPath) -> Callable[[RouteFunction], RouteFunction]:
    """Add a DELETE route to a function."""

    def wrapper(fn: RouteFunction) -> RouteFunction:
        routes: dict[HttpMethod, Iterable[UrlPath]] = {HttpMethod.DELETE: (path,)}
        _add_routes(routes, fn)
        return fn

    return wrapper


def post(path: UrlPath) -> Callable[[RouteFunction], RouteFunction]:
    """Add a POST route to a function."""

    def wrapper(fn: RouteFunction) -> RouteFunction:
        routes: dict[HttpMethod, Iterable[UrlPath]] = {HttpMethod.POST: (path,)}
        _add_routes(routes, fn)
        return fn

    return wrapper


def put(path: UrlPath) -> Callable[[RouteFunction], RouteFunction]:
    """Add a PUT route to a function."""

    def wrapper(fn: RouteFunction) -> RouteFunction:
        routes: dict[HttpMethod, Iterable[UrlPath]] = {HttpMethod.PUT: (path,)}
        _add_routes(routes, fn)
        return fn

    return wrapper


def patch(path: UrlPath) -> Callable[[RouteFunction], RouteFunction]:
    """Add a PATCH route to a function."""

    def wrapper(fn: RouteFunction) -> RouteFunction:
        routes: dict[HttpMethod, Iterable[UrlPath]] = {HttpMethod.PATCH: (path,)}
        _add_routes(routes, fn)
        return fn

    return wrapper


def _add_routes(
    routes: MutableMapping[HttpMethod, Iterable[UrlPath]],
    fn: RouteFunction,
) -> RouteFunction:
    if getattr(fn, "__routes__", None) is None:
        fn.__routes__ = collections.defaultdict(set)

    for method, paths in routes.items():
        fn.__routes__[method.value].update(paths)

    return fn
