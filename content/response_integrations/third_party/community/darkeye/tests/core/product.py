from __future__ import annotations

import dataclasses

from TIPCommon.types import SingleJson


@dataclasses.dataclass(slots=True)
class DarkEye:
    """In-memory HaveIBeenRansom and Breach House."""

    haveibeenransom_pages: dict[tuple[str, str], list[SingleJson]] = dataclasses.field(default_factory=dict)
    breach_house_searches: dict[str, SingleJson] = dataclasses.field(default_factory=dict)
    failures: dict[str, int] = dataclasses.field(default_factory=dict)

    def set_haveibeenransom_pages(self, field: str, term: str, pages: list[SingleJson]) -> None:
        self.haveibeenransom_pages[field, term] = pages

    def set_breach_house_search(self, term: str, response: SingleJson) -> None:
        self.breach_house_searches[term] = response

    def fail(self, product: str, status_code: int) -> None:
        self.failures[product] = status_code

    def get_haveibeenransom_page(self, field: str, term: str, page: int) -> SingleJson:
        pages: list[SingleJson] = self.haveibeenransom_pages.get((field, term), [])
        if page > len(pages):
            return {"success": True, "sources": [], "has_next": False}
        return pages[page - 1]

    def get_breach_house_search(self, term: str) -> SingleJson:
        return self.breach_house_searches.get(term, {"ransomware": [], "breaches": [], "leads": [], "stealers": []})
