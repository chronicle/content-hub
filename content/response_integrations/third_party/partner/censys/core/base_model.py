from __future__ import annotations

from TIPCommon.types import SingleJson


class BaseModel(object):
    """
    Base data model class for all Censys API responses.
    Provides common functionality for data transformation and output formatting.
    """

    def __init__(self, raw_data: SingleJson | None = None) -> None:
        """
        Initialize the base model.

        Args:
            raw_data: Raw API response data
        """
        self.raw_data = raw_data or {}
        # Subclasses that extract a resource dict (e.g. self.host_data,
        # self.web_data, self.cert_data) should also assign it here so the
        # shared is_found() below works without each subclass redefining it.
        self._resource_data: SingleJson = {}

    def is_found(self) -> bool:
        """
        Check if the extracted resource data was found.

        Returns:
            bool: True if resource data exists
        """
        return bool(self._resource_data)

    def to_json(self) -> SingleJson:
        """
        Convert the model to JSON format.

        Returns:
            Dict containing the raw API response data
        """
        return self.raw_data

    def to_csv(self) -> list[SingleJson]:
        """
        Convert the model to CSV format.
        Should be overridden by child classes.

        Returns:
            List of dictionaries suitable for CSV output
        """
        return [self.raw_data] if self.raw_data else []

    def _get_top_values(self, values: list[object], max_count: int = 5) -> str | None:
        """
        Get top N unique values as comma-separated string.

        Args:
            values: List of values to process
            max_count: Maximum number of values to return

        Returns:
            Comma-separated string of top values or None
        """
        if not values:
            return None

        unique_values: list[str] = []
        seen: set[str] = set()
        for val in values:
            if not val:
                continue

            # Handle dict values (like vulnerability objects)
            if isinstance(val, dict):
                val_str = val.get("id") or str(val)
            else:
                val_str = str(val)

            # Use string representation for deduplication
            if val_str not in seen:
                unique_values.append(val_str)
                seen.add(val_str)
                if len(unique_values) >= max_count:
                    break

        return ", ".join(unique_values) if unique_values else None
