from __future__ import annotations
import abc

import dataclasses
from typing import Any, MutableMapping


@dataclasses.dataclass
class OpenSearchProduct(abc.ABC):
    """Represents a mock OpenSearch cluster's data store."""

    def __init__(self):
        # A dictionary to hold mock indices and their documents
        super().__init__()
        self._indices: MutableMapping[str, list[Any]] = {}
        self._cluster_info: dict = {}
        self._search_results: dict = {}

    def set_cluster_info(self, info: dict) -> None:
        self._cluster_info = info

    def get_cluster_info(self) -> dict:
        return self._cluster_info

    def set_search_results(self, results: dict) -> None:
        self._search_results = results

    def get_search_results(self) -> dict:
        return self._search_results

    def index_exists(self, index_name: str) -> bool:
        return index_name in self._indices
