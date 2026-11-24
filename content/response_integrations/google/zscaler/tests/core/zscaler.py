from __future__ import annotations
import abc

import dataclasses
from typing import Any, ClassVar


@dataclasses.dataclass
class Zscaler(abc.ABC):
    """
    Imitates the Zscaler product backend state.
    """

    expected_api_key: ClassVar[str] = "obfuscated_key"

    whitelist_urls: list[str] = dataclasses.field(default_factory=list)
    blacklist_urls: list[str] = dataclasses.field(default_factory=list)
    mock_data: dict[str, Any] = dataclasses.field(default_factory=dict)

    def add_to_whitelist(self, urls_to_add: list[str]) -> None:
        """Adds new URLs to the whitelist, avoiding duplicates."""
        for url in urls_to_add:
            if url not in self.whitelist_urls:
                self.whitelist_urls.append(url)
