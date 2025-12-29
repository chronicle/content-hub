from __future__ import annotations

from typing import TYPE_CHECKING

from soar_sdk.SiemplifyUtils import unix_now

from .constants import (
    DEFAULT_ASSET_LIMIT,
    DEFAULT_MAX_LIMIT,
    DEFAULT_OFFSET,
    DEFAULT_RESULTS_LIMIT,
    HIGHEST_POSSIBLE_SCORE,
    POSSIBLE_SEVERITIES,
    BLACKLIST_FILTER,
    WHITELIST_FILTER,
)

if TYPE_CHECKING:
    from typing import Any


class BaseQueryBuilder:
    def __init__(self) -> None:
        self.payload: dict[str, Any] = {
            "query": {
                "models": [],
                "type": "object_set",
                "with": {"operator": "and", "type": "operation", "values": []},
            },
            "limit": DEFAULT_RESULTS_LIMIT,
            "start_at_index": DEFAULT_OFFSET,
        }

    def _add_filter(
        self,
        key: str,
        values: list[Any],
        type_str: str,
        operator: str,
        value_type: str | None = None,
    ) -> None:
        """Adds a filter dictionary to the query values.
        Args:
            key (str): The key to filter by.
            values (list[Any]): The values to filter by.
            type_str (str): The type of the values.
            operator (str): The operator to use for the filter.
            value_type (str | None): The value type to use for the filter.
        """
        filter_dict: dict[str, Any] = {
            "key": key,
            "values": values,
            "type": type_str,
            "operator": operator,
        }
        if value_type:
            filter_dict["value_type"] = value_type

        self.values.append(filter_dict)

    @property
    def values(self) -> list[dict[str, Any]]:
        return self.payload["query"]["with"]["values"]

    def build(self) -> dict[str, Any]:
        return self.payload


class AlertQueryBuilder(BaseQueryBuilder):
    def __init__(
        self,
        start_timestamp: int | None = None,
        limit: int = DEFAULT_MAX_LIMIT,
    ) -> None:
        super().__init__()
        self.payload["limit"] = limit
        self.payload["query"]["models"] = ["Alert"]
        self.payload["order_by[]"] = ["CreatedAt"]

        if start_timestamp is not None:
            self.with_created_at_range(start_timestamp)

    def with_created_at_range(self, start_timestamp: int) -> AlertQueryBuilder:
        """Create a range filter for CreatedAt field.
        Args:
            start_timestamp (int): The start timestamp to filter by.

        Returns:
            AlertQueryBuilder: The instance of the builder.
        """
        self._add_filter(
            key="CreatedAt",
            values=[start_timestamp, unix_now()],
            type_str="datetime",
            operator="date_range",
            value_type="days",
        )
        return self

    def with_alert_id(self, alert_id: str) -> AlertQueryBuilder:
        """Create a filter for AlertId field.
        Args:
            alert_id (str): The alert ID to filter by.

        Returns:
            AlertQueryBuilder: The instance of the builder.
        """
        self._add_filter("AlertId", [alert_id], "str", "in")
        return self

    def with_severity(self, lowest_severity: str) -> AlertQueryBuilder:
        """Create a filter for Severity field.

        Args:
            lowest_severity (str): The lowest severity to filter by.

        Returns:
            AlertQueryBuilder: The instance of the builder.
        """
        if lowest_severity:
            self._add_filter(
                "Severity",
                POSSIBLE_SEVERITIES[: POSSIBLE_SEVERITIES.index(lowest_severity) + 1],
                "str",
                "in",
            )

        return self

    def with_categories(self, categories: list[str]) -> AlertQueryBuilder:
        """Create a filter for Category field.

        Args:
            categories (list[str]): List of categories to filter by.

        Returns:
            AlertQueryBuilder: The instance of the builder.
        """
        if categories:
            self._add_filter("Category", categories, "str", "in")

        return self

    def with_title_filter(
        self,
        title_filter: list[str],
        filter_type: int = WHITELIST_FILTER,
    ) -> AlertQueryBuilder:
        """Create a filter for Title field.
        Args:
            title_filter (list[str]): List of titles to filter by.
            filter_type (int): The type of filter, either WHITELIST_FILTER or
            BLACKLIST_FILTER.

        Returns:
            AlertQueryBuilder: The instance of the builder.
        """
        if title_filter:
            operator = "not_in" if filter_type == BLACKLIST_FILTER else "in"
            self._add_filter("Title", title_filter, "str", operator)

        return self

    def with_alert_types(self, alert_types: list[str]) -> AlertQueryBuilder:
        """Create a filter for RuleType field.
        Args:
            alert_types (list[str]): List of alert types to filter by.

        Returns:
            AlertQueryBuilder: The instance of the builder.
        """
        if alert_types:
            self._add_filter("AlertType", alert_types, "str", "in")

        return self

    def with_score(self, lowest_score: float) -> AlertQueryBuilder:
        """Create a range filter for Score field.
        Args:
            lowest_score (float): The lowest score to filter by.

        Returns:
            AlertQueryBuilder: The instance of the builder.
        """
        if lowest_score:
            self._add_filter(
                "OrcaScore",
                [lowest_score, HIGHEST_POSSIBLE_SCORE],
                "float",
                "range",
            )

        return self


class AssetQueryBuilder(BaseQueryBuilder):
    def __init__(self, limit: int = DEFAULT_ASSET_LIMIT) -> None:
        super().__init__()
        self.payload["limit"] = limit
        self.payload["query"]["models"] = ["Inventory"]

    def with_asset_id(self, asset_id: str | list[str]) -> AssetQueryBuilder:
        """Create a filter for asset_unique_id field.
        Args:
            asset_id (str | list[str]): The asset ID or list of asset IDs to filter by.

        Returns:
            AssetQueryBuilder: The instance of the builder.
        """
        if isinstance(asset_id, str):
            asset_id = [asset_id]

        self._add_filter("asset_unique_id", asset_id, "str", "in")

        return self
