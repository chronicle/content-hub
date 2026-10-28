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
import abc
from dataclasses import asdict, dataclass
from typing import Any

import requests

from crowd_strike_falcon.core.CrowdStrikeParser import CrowdStrikeParser


parser = CrowdStrikeParser()


class PaginationStrategy(abc.ABC):

    @abc.abstractmethod
    def get_initial_state(self) -> dict[str, Any]:
        """Gets the initial state for the pagination strategy.

        Returns:
            A dictionary representing the initial state.
        """

    @abc.abstractmethod
    def has_next_page(self, last_page_count: int, total: int) -> bool:
        """Checks if there is a next page of results.

        Args:
            last_page_count: The number of items in the last retrieved page.
            total: The total number of items available.

        Returns:
            True if there is a next page, False otherwise.
        """

    @abc.abstractmethod
    def get_next_page_state(self) -> dict:
        """Gets the state required to fetch the next page.

        Returns:
            A dictionary representing the state for the next page request.
        """

    @abc.abstractmethod
    def update_next_page_token(self, response: requests.Response) -> None:
        """Updates the internal state for fetching the next page.

        Args:
            response: The response object from the last API request.
        """


@dataclass
class OffsetPaginationStrategy(PaginationStrategy):
    limit: int
    offset: int = 0

    def get_initial_state(self) -> dict[str, Any]:
        return {"limit": self.limit, "offset": 0}

    def has_next_page(self, last_page_count: int, total: int) -> bool:
        """Checks if there is a next page of results to fetch.

        This method determines if a subsequent page of results exists by checking
        two conditions: whether the last page was full and if all available items
        have been fetched.

        Args:
            last_page_count: The number of items in the last retrieved page.
            total: The total number of items available.

        Returns:
            True if there is a next page, False otherwise.
        """
        if last_page_count < self.limit:
            return False

        return (self.offset + last_page_count) < total

    def get_next_page_state(self) -> dict[str, Any]:
        return asdict(self)

    def update_next_page_token(self, _: requests.Response) -> None:
        self.offset += self.limit


@dataclass
class TokenPaginationStrategy(OffsetPaginationStrategy):
    after: str = None

    def get_initial_state(self) -> dict[str, Any]:
        return {"limit": self.limit}

    def get_next_page_state(self) -> dict:
        return {"limit": self.limit, "after": self.after}

    def update_next_page_token(self, response: requests.Response) -> None:
        super().update_next_page_token(response)
        self.after = parser.get_page_after_token(response.json())
