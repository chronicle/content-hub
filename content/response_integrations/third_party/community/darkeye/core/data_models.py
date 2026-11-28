from __future__ import annotations

import dataclasses
from typing import Any

from .constants import RECORD_TABLE_HEADERS
from .utils import clean


@dataclasses.dataclass(slots=True, frozen=True)
class Record:
    """One listing found by a DarkEye product. Only listing metadata is kept."""

    product: str
    category: str
    id: str
    title: str
    website: str
    group: str
    country: str
    discovered: str

    @classmethod
    def from_api(cls, product: str, category: str, item: dict[str, Any]) -> Record:
        """Build a record from an API item.

        Leaked content, leak-site URLs and download links are never read.

        Args:
            product: The product that returned the item.
            category: The category of the item.
            item: The item from the API response.

        Returns:
            Record: The record.
        """
        website: str = clean(item.get("website"))
        return cls(
            product=product,
            category=category,
            id=clean(item.get("id_source") or item.get("victim_id") or item.get("id")),
            title=clean(item.get("post_title")) or clean(item.get("name")) or website,
            website=website,
            group=clean(item.get("group_name")),
            country=clean(item.get("country")),
            discovered=clean(item.get("discovered"))[:10],
        )

    def to_json(self) -> dict[str, str]:
        return {
            "product": self.product,
            "category": self.category,
            "id": self.id,
            "title": self.title,
            "website": self.website,
            "group": self.group,
            "country": self.country,
            "discovered": self.discovered,
        }

    def to_table_row(self) -> dict[str, str]:
        values: tuple[str, ...] = (
            self.product,
            self.category,
            self.title,
            self.website,
            self.group,
            self.country,
            self.discovered,
            self.id,
        )
        return dict(zip(RECORD_TABLE_HEADERS, values, strict=True))


@dataclasses.dataclass(slots=True)
class ProductResult:
    """What one product returned for one entity."""

    records: list[Record] = dataclasses.field(default_factory=list)
    truncated: bool = False


@dataclasses.dataclass(slots=True)
class EntityResult:
    """The combined DarkEye result for one entity."""

    entity: str
    entity_type: str
    products: list[str] = dataclasses.field(default_factory=list)
    errors: list[dict[str, str]] = dataclasses.field(default_factory=list)
    records: list[Record] = dataclasses.field(default_factory=list)
    truncated: bool = False

    def add(self, product: str, result: ProductResult) -> None:
        self.products.append(product)
        self.records.extend(result.records)
        self.truncated = self.truncated or result.truncated

    def add_error(self, product: str, error: str) -> None:
        self.errors.append({"product": product, "error": error})

    @property
    def counts_by_product(self) -> dict[str, int]:
        counts: dict[str, int] = dict.fromkeys(self.products, 0)
        for record in self.records:
            counts[record.product] += 1
        return counts

    @property
    def counts_by_category(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for record in self.records:
            counts[record.category] = counts.get(record.category, 0) + 1
        return counts

    def to_json(self) -> dict[str, Any]:
        return {
            "entity": self.entity,
            "entity_type": self.entity_type,
            "found": bool(self.records),
            "count": len(self.records),
            "products": self.products,
            "counts_by_product": self.counts_by_product,
            "counts_by_category": self.counts_by_category,
            "truncated": self.truncated,
            "errors": self.errors,
            "records": [record.to_json() for record in self.records],
        }

    def to_enrichment(self) -> dict[str, str]:
        """Flat enrichment fields for the entity, without the records themselves."""
        categories: str = ", ".join(f"{name}: {count}" for name, count in sorted(self.counts_by_category.items()))
        return {
            "found": str(bool(self.records)).lower(),
            "count": str(len(self.records)),
            "products": ", ".join(self.products),
            "categories": categories,
            "truncated": str(self.truncated).lower(),
        }
