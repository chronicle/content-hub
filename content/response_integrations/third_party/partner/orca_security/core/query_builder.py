from __future__ import annotations

from typing import TYPE_CHECKING

from soar_sdk.SiemplifyUtils import unix_now

from .constants import (
    BLACKLIST_FILTER,
    DEFAULT_ASSET_LIMIT,
    DEFAULT_MAX_LIMIT,
    DEFAULT_OFFSET,
    DEFAULT_RESULTS_LIMIT,
    HIGHEST_POSSIBLE_SCORE,
    POSSIBLE_SEVERITIES,
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

    def start_at_index(self, index: int) -> BaseQueryBuilder:
        """Set the starting index for the query results.
        Args:
            index (int): The starting index.
        Returns:
            BaseQueryBuilder: The instance of the builder.
        """
        self.payload["start_at_index"] = index
        return self

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


class VulnerabilityQueryBuilder:
    """Builder class for constructing vulnerability queries in the new API format."""

    def __init__(self, limit: int = DEFAULT_RESULTS_LIMIT) -> None:
        self.limit: int = limit
        self.models: list[str] = ["VulnerabilityV2"]  # Main models for new API
        self.keys: list[str] = ["Inventory"]  # Keys for with clause
        self.nested_models: list[str] = ["Inventory"]  # Models for with clause
        self.cve_ids: list[str] = []  # Keep for backward compatibility
        self.start_index: int = DEFAULT_OFFSET
        self.get_results_and_count: bool = False
        self.select_fields: list[str] = []
        # New parameters for updated API
        self.additional_models: list[str] = ["InstalledPackage", "Inventory"]
        self.flat_json: bool = True
        self.full_graph_fetch: dict[str, bool] = {"enabled": True}
        self.asset_unique_id: list[str] = []
        self.severity: list[str] = []
        self.order_by: list[str] = []
        self.max_tier: int = 2

    def with_results_and_count(self, value: bool = False) -> VulnerabilityQueryBuilder:
        """
        Set the flag to get both results and count in the response.
        Args:
            value (bool): Whether to get results and count. Default is False.
        Returns:
            VulnerabilityQueryBuilder: The instance of the builder.
        """
        self.get_results_and_count = value
        return self

    def select(self, fields: list[str]) -> VulnerabilityQueryBuilder:
        """Set the fields to select in the query results.
        Args:
            fields (list[str]): The list of fields to select.
        Returns:
            VulnerabilityQueryBuilder: The instance of the builder.
        """
        self.select_fields = fields
        return self

    def start_at_index(self, index: int) -> VulnerabilityQueryBuilder:
        """Set the starting index for the query results.
        Args:
            index (int): The starting index.
        Returns:
            VulnerabilityQueryBuilder: The instance of the builder.
        """
        self.start_index = index
        return self

    def with_cve_id(self, cve_id: str | list[str]) -> VulnerabilityQueryBuilder:
        """Create a filter for cve_id field.
        Args:
            cve_id (str | list[str]): The CVE ID or list of CVE IDs to filter by.

        Returns:
            VulnerabilityQueryBuilder: The instance of the builder.
        """
        if isinstance(cve_id, str):
            self.cve_ids = [cve_id]
        else:
            self.cve_ids = cve_id

        return self

    def with_asset_unique_id(self, value: str | list[str]) -> VulnerabilityQueryBuilder:
        """
        Create a filter for asset_unique_id field in the nested Inventory model.
        Args:
            value (str | list[str]): The asset unique ID or list of asset unique IDs to
            filter by.
        Returns:
            VulnerabilityQueryBuilder: The instance of the builder.
        """
        if isinstance(value, str):
            self.asset_unique_id = [value]
        else:
            self.asset_unique_id = value

        return self

    def with_severity(self, severity: str | list[str]) -> VulnerabilityQueryBuilder:
        """
        Create a filter for severity field.
        Args:
            severity (str | list[str]): The severity or list of severities to filter by.
        Returns:
            VulnerabilityQueryBuilder: The instance of the builder.
        """
        if isinstance(severity, str):
            self.severity = [severity]
        else:
            self.severity = severity

        return self

    def with_order_by(self, fields: list[str] | str) -> VulnerabilityQueryBuilder:
        """
        Set the fields to order the query results by.
        Args:
            fields (list[str]): The list of fields to order by.
        Returns:
            VulnerabilityQueryBuilder: The instance of the builder.
        """
        if isinstance(fields, str):
            self.order_by = [fields]
        else:
            self.order_by = fields
        return self

    def build(self) -> dict[str, Any]:
        """Build the vulnerability query in the new API format.

        Returns:
            dict[str, Any]: The complete payload.
        """
        query = {
            "models": self.models,  # ["VulnerabilityV2"]
            "type": "object_set",
            "with": {
                "operator": "and",
                "type": "operation",
                "values": [
                    {
                        "keys": self.keys,
                        "models": self.nested_models,
                        "type": "object",
                        "operator": "has",
                    },
                ],
            },
        }

        if self.cve_ids:
            query["with"]["values"].append({
                "key": "CveId",
                "values": self.cve_ids,
                "type": "str",
                "operator": "in",
            })

        if self.asset_unique_id:
            query["with"]["values"].append({
                "keys": ["Inventory"],
                "models": ["Inventory"],
                "type": "object",
                "operator": "has",
                "with": {
                    "key": "AssetUniqueId",
                    "values": self.asset_unique_id,
                    "type": "str",
                    "operator": "in",
                },
            })

        if self.severity:
            query["with"]["values"].append({
                "key": "CvssSeverity",
                "values": self.severity,
                "type": "str",
                "operator": "in",
            })

        # Build the payload with new structure
        payload = {
            "query": query,
            "limit": self.limit,
            "start_at_index": self.start_index,
            "get_results_and_count": self.get_results_and_count,
            "additional_models[]": self.additional_models,
            "flat_json": self.flat_json,
            "full_graph_fetch": self.full_graph_fetch,
            "max_tier": self.max_tier,
        }

        if self.order_by:
            payload["order_by[]"] = self.order_by

        # Add select fields if specified
        if self.select_fields:
            payload["select"] = self.select_fields

        return payload
