from __future__ import annotations
import abc
from dataclasses import asdict, dataclass
from typing import Any

import requests


class PaginationStrategy(abc.ABC):

    @abc.abstractmethod
    def get_initial_state(self) -> dict[str, Any]:
        """Gets the initial state for the pagination strategy.

        Returns:
            A dictionary representing the initial state.
        """

    @abc.abstractmethod
    def has_next_page(self, last_page_count: int) -> bool:
        """Checks if there is a next page of results.

        Args:
            last_page_count: The number of items in the last retrieved page.

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
class V2OffsetPaginationStrategy(PaginationStrategy):
    limit: int
    offset: int = 0

    def get_initial_state(self) -> dict[str, Any]:
        return {"limit": self.limit, "offset": 0}

    def has_next_page(self, last_page_count: int) -> bool:
        return last_page_count >= self.limit

    def get_next_page_state(self) -> dict[str, Any]:
        return asdict(self)

    def update_next_page_token(self, _: requests.Response) -> None:
        self.offset += self.limit


@dataclass
class V1SkipPaginationStrategy(PaginationStrategy):
    limit: int
    skip: int = 0

    def get_initial_state(self) -> dict[str, Any]:
        return {"limit": self.limit, "skip": 0}

    def has_next_page(self, last_page_count: int) -> bool:
        return last_page_count >= self.limit

    def get_next_page_state(self) -> dict[str, Any]:
        return asdict(self)

    def update_next_page_token(self, _: requests.Response) -> None:
        self.skip += self.limit
