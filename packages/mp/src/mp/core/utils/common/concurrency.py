"""Module containing concurrency utilities."""

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

import logging
from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from typing import TYPE_CHECKING, TypeVar

import mp.core.config

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable

logger: logging.Logger = logging.getLogger(__name__)

_T = TypeVar("_T")


class ParallelRunError(Exception):
    """Generic exception type for errors during parallel execution of a command."""

    def __init__(self, message: str, errors: list[tuple] | None = None) -> None:
        super().__init__(message)
        self.errors = errors or []


def run_in_parallel(
    func: Callable[[_T], object], items: Iterable[_T], max_workers: int, error_message_template: str
) -> None:
    """Run a function in parallel over a list of items and aggregate errors.

    Args:
        func: The function to execute.
        items: The iterable of items to pass to the function.
        max_workers: The number of worker threads to use.
        error_message_template: Template string for the error message (e.g. "Failed to process '%s'").
            It will be formatted with the item's name or string representation.

    Raises:
        ParallelRunError: If any of the executions fail.

    """
    errors: list[tuple[_T, Exception]] = []
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures: dict[Future[object], _T] = {pool.submit(func, item): item for item in items}
        for future in as_completed(futures):
            item: _T = futures[future]
            try:
                future.result()
            except Exception as e:  # noqa: BLE001
                errors.append((item, e))

    if errors:
        try:
            is_verbose: bool = mp.core.config.is_verbose()
        except ValueError:
            is_verbose = False

        for item, e in errors:
            item_name: str = getattr(item, "name", str(item))
            if is_verbose:
                logger.error(error_message_template, item_name, exc_info=e)
            else:
                error_msgs: list[str] = []
                curr: BaseException | None = e
                while curr:
                    error_msgs.append(f"{type(curr).__name__}: {curr}")
                    # Prioritize __cause__ over __context__ for 'raise X from Y' semantics
                    curr: BaseException | None = curr.__cause__ or curr.__context__

                chain_str: str = " -> ".join(error_msgs)
                logger.error(f"{error_message_template}:\n  %s", item_name, chain_str)  # noqa: G004

        msg: str = f"Failed to process {len(errors)} item(s)."
        raise ParallelRunError(msg, errors)
