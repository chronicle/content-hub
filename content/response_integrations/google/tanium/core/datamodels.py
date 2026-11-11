from __future__ import annotations
import copy
import json

from collections.abc import Callable, Generator
from typing import Any

from tanium.core.constants import ENRICHMENT_PREFIX, MAX_QUESTION_RESULTS_DEFAULT
from TIPCommon import dict_to_flat, add_prefix_to_dict

from tanium.core.exceptions import TaniumResponseSchemaError


class BaseModel:
    def __init__(self, raw_data):
        self.raw_data = raw_data

    def to_json(self):
        return self.raw_data

    def to_flat(self):
        return dict_to_flat(self.to_json())


class Question(BaseModel):
    def __init__(self, raw_data, **kwargs):
        super().__init__(raw_data)
        self.id = raw_data.get("data", {}).get("id", 0)


class QuestionResultFullData(BaseModel):
    rows: list[list[list[str]]]
    columns: list[str]
    expire_seconds: int
    seconds_since_issued: int

    def __init__(
        self,
        rows: list[list[list[str]]],
        columns: list[str],
        expire_seconds: int,
        seconds_since_issued: int,
        raw_data: dict[str, Any],
    ) -> None:
        """Initializes the QuestionResultFullData instance.

        Args:
            rows: A list of rows, where each row is a list of cells.
                Each cell is a `list[str]`, and its index within the
                row list corresponds to its column.
            columns: A list of column names.
            raw_data: The raw dictionary data for the result set.
        """
        self.rows = rows
        self.columns = columns
        self.expire_seconds = expire_seconds
        self.seconds_since_issued = seconds_since_issued

        super().__init__(raw_data)

    @classmethod
    def from_raw_response(
        cls, raw_data: dict[str, Any], limit: int = MAX_QUESTION_RESULTS_DEFAULT
    ) -> "QuestionResultFullData":
        """Creates a new instance from a raw API response dictionary.

        Parses the nested 'result_sets' from the raw response,
        processes and limits the 'rows', and truncates the 'columns'.
        It specifically removes the last element from each row's 'data' list
        and the last element from the top-level 'columns' list.

        Args:
            raw_data: The raw API response, expected to
                contain a 'data' key with 'result_sets'.
            limit: The maximum number of rows to process and include in
                the new instance. Defaults to `MAX_QUESTION_RESULTS_DEFAULT`.

        Returns:
            A new instance of the class populated with
            the processed data from the first result set found.

        Raises:
            TaniumResponseSchemaError: If a column name is missing or if
                the number of cells in a row does not match the
                number of columns.
        """
        result_set = raw_data.get("data", {}).get("result_sets", [])
        result_set = result_set[0] if result_set else {}

        truncated_column_objects = result_set.get("columns", [])[:-1]
        columns = cls._extract_by_name(
            data_items=truncated_column_objects, field="name"
        )
        if len(truncated_column_objects) != len(columns):
            raise TaniumResponseSchemaError(
                "Failed to parse column names from response; 'name' field missing in "
                "one or more column objects"
            )

        rows = [
            [
                # Extracting cell values from [{"text": "0.0.0.0"}, ...]
                cls._extract_by_name(data_items=cell_data, field="text")
                # For all cells except the last one (Count cell must be dropped)
                for cell_data in row["data"][:-1]
            ]
            # For all rows but no more than given `limit`
            for row in result_set.get("rows", [])[:limit]
        ]

        for row in rows:
            # After extracting all fields, ensure all are present
            # and that row cells align with their column positions.
            if len(row) != len(columns):
                msg = (
                    "The number of cells in the row does not match the number of "
                    f"columns. Rows: {len(row)}, columns: {len(columns)}"
                )
                raise TaniumResponseSchemaError(msg)

        return cls(
            rows=rows,
            columns=columns,
            expire_seconds=result_set.get("expire_seconds"),
            seconds_since_issued=result_set.get("seconds_since_issued"),
            raw_data=result_set
        )

    @staticmethod
    def _extract_by_name(data_items: list[dict[str, Any]], field: str) -> list[str]:
        """Extracts values from a list of data dictionaries based on a key.

        Args:
            data_items: A list of dictionaries, where each dictionary
                may contain the specified `field`.
            field: The name of the data item to extract.

        Returns:
            A list of strings containing all non-None values found for
            the given `field`.
        """
        return [
            item.get(field) for item in data_items if item.get(field) is not None
        ]

    def _iter_normalize_rows(
        self, value_formatter: Callable[[list[str]], Any] = None
    ) -> Generator[dict[str, Any], None, None]:
        """Iterates over rows, mapping column names to cell values.

        Applies an optional formatter to each cell's list of values.

        Args:
            value_formatter: An optional callable that takes a list of strings
                (the text values from a cell) and returns a single formatted
                value.

        Yields:
            A dictionary representing a processed row, where keys are
            column names and values are the extracted (and possibly
            formatted) cell data.
        """
        for row in self.rows:
            processed_row = {}
            for col_name, cell_data_items in zip(self.columns, row):
                processed_row[col_name] = (
                    value_formatter(cell_data_items) if value_formatter
                    else cell_data_items
                )
            yield processed_row

    def to_json(self) -> str:
        """Serializes the object's data into a JSON string.

        Returns:
            A JSON-formatted string of the processed data. Returns `{}`
            if the instance's `raw_data` attribute is empty.
        """
        if not self.raw_data:
            return "{}"

        output_data = {
            k: v for k, v in self.raw_data.items() if k not in {"rows", "columns"}
        }
        # Populating output data with original columns values excluding `Count`
        output_data["columns"] = self.raw_data.get("columns", [])[:-1]

        output_data["rows"] = list(self._iter_normalize_rows())

        return json.dumps(output_data)

    def to_csv_lines(self, multi_value_delimiter: str = ", ") -> list[dict[str, Any]]:
        """Converts the instance's row data into a list of dicts.

        Each row's data is processed. If a single cell contains multiple
        text values, they are joined together using the specified delimiter.

        Args:
            multi_value_delimiter: The string used to join multiple text
                values found within a single cell.

        Returns:
            A list of dicts. Each dict represents a CSV row
        """
        return list(
            self._iter_normalize_rows(value_formatter=multi_value_delimiter.join)
        )


class QuestionResult(BaseModel):
    def __init__(self, raw_data, short_raw_data, columns, rows):
        super().__init__(raw_data)
        self.short_raw_data = short_raw_data
        self.columns = columns
        self.rows = rows

    def to_json(self):
        raw_data = copy.deepcopy(self.short_raw_data)
        columns = copy.deepcopy(self.columns)
        rows = copy.deepcopy(self.rows)

        for row in rows:
            row["data"] = row["data"][0]

        raw_data.update({"columns": columns[:-1], "rows": rows})

        return raw_data

    def to_csv(self):
        csv = []
        for row in self.rows:
            if row.get("data", []):
                csv.append(
                    {
                        self.columns[0]
                        .get("name", ""): row.get("data", [])[0][0]
                        .get("text")
                    }
                )

        return csv

    def to_enrichment_json(self):
        columns = copy.deepcopy(self.columns)[:-1]
        raw_json = {}

        for index, value in enumerate(columns):
            raw_key = value.get("name", "")
            if len(self.rows[0].get("data")[index]) > 1:
                raw_data = ", ".join(
                    [item.get("text") for item in self.rows[0].get("data")[index]]
                )
            else:
                raw_data = self.rows[0].get("data")[index][0].get("text")
            raw_json[raw_key] = raw_data

        return raw_json

    def to_enrichment_csv(self):
        return dict_to_flat(self.to_enrichment_json())

    def to_enrichment(self):
        data = self.to_enrichment_json()
        enrichment_data = {}
        for key, val in data.items():
            replaced_key = key.replace(" ", "_")
            enrichment_data[replaced_key] = val

        return add_prefix_to_dict(enrichment_data, ENRICHMENT_PREFIX)


class Connection(BaseModel):
    def __init__(self, raw_data, id, ip, hostname, client_id, platform, status):
        super().__init__(raw_data)
        self.id = id
        self.ip = ip
        self.hostname = hostname
        self.client_id = client_id
        self.platform = platform
        self.status = status


class EndpointDetails(BaseModel):
    def __init__(self, raw_data, ip, hostname, client_id, platform, status):
        super().__init__(raw_data)
        self.ip = ip
        self.hostname = hostname
        self.client_id = client_id
        self.platform = platform
        self.status = status


class Task(BaseModel):
    def __init__(self, raw_data, id, status, file_uuid, file_path, meta_type, meta_id):
        super().__init__(raw_data)
        self.id = id
        self.status = status
        self.file_uuid = file_uuid
        self.file_path = file_path
        self.meta_type = meta_type
        self.meta_id = meta_id
