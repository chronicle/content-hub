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

import datetime
import json
import os
from typing import Any

import pandas as pandas

from TIPCommon.transformation import construct_csv, dict_to_flat

from csv_integration.core.datamodels import CSVItem
from csv_integration.core.exceptions import CSVEncodingException, CSVJsonIsInvalidError
from csv_integration.core.utils import (
    flatten_json_vertically,
    get_file_path,
    get_value_for_search,
)


# CONSTANTS
CSV_EXTENSION = ".csv"
ENRICHMENT_PREFIX = "CSVEnrichment"
FILE_ENCODINGS_DEFAULT = ["utf-8", "latin-1", "iso-8859-1"]


class CSVManager:
    def __init__(self, siemplify):
        self.siemplify = siemplify

    @staticmethod
    def is_csv_file_pass_time_filter(file_path, days_back=None):
        """
        Check if file is CSV file and if stands in time restriction
        :param file_path: {str} file path
        :param days_back: {str} how many days back to look for
        :return: {str} is file valid
        """
        pass_time_filter = True
        if days_back:
            start_from_date = datetime.datetime.now() - datetime.timedelta(
                days=int(days_back)
            )
            pass_time_filter = (
                datetime.datetime.fromtimestamp(os.path.getctime(file_path))
                > start_from_date
            )

        is_csv_file = os.path.splitext(file_path)[1] == CSV_EXTENSION
        return is_csv_file and pass_time_filter

    @staticmethod
    def get_csv_paths(csv_folder_or_file_path, order_by_time=True):
        paths = []
        if os.path.isdir(csv_folder_or_file_path):
            for dir_name in os.listdir(csv_folder_or_file_path):
                if os.path.isfile(os.path.join(csv_folder_or_file_path, dir_name)):
                    paths.append(os.path.join(csv_folder_or_file_path, dir_name))
        else:
            paths.append(csv_folder_or_file_path)

        if order_by_time:
            paths = sorted(paths, key=lambda path: os.path.getmtime(path), reverse=True)

        return paths

    def get_relevant_csv_files(
        self, csv_folder_or_file_path, days_back=None, csv_count_limit=None
    ):
        """
        Return the relevant ioc's files according to time limit
        :param csv_folder_or_file_path: {string} file path or folder path
        :param days_back: {str} how many days back to look for
        :param csv_count_limit: {int} Process csv files based on the given limit in every cycle. e.g. 10
        return: {list} of strings
        """
        return [
            path
            for path in self.get_csv_paths(csv_folder_or_file_path)
            if self.is_csv_file_pass_time_filter(path, days_back)
        ][:csv_count_limit]

    def read_csv(self, csv_path, file_encodings, file_has_header=True):
        """
        Read CSV by path
        :param csv_path: {str} full path of the csv file
        :param file_encodings: {list} List of possible CSV encodings
        :param file_has_header: {list} List of possible CSV encodings
        :return {pandas.core.frame.DataFrame}
        """
        for file_encoding in file_encodings:
            try:
                read_params = {
                    "filepath_or_buffer": csv_path,
                    "encoding": file_encoding,
                }
                if not file_has_header:
                    read_params["header"] = None

                return pandas.read_csv(**read_params)
            except Exception as e:
                self.siemplify.LOGGER.error(
                    f"Failed to read file {csv_path}. Error is {e}"
                )
                self.siemplify.LOGGER.exception(e)
        raise CSVEncodingException(
            f"Failed reading file {csv_path} with all given encodings "
            f"{file_encodings}, please specify some other "
            f"encoding so we can process your files. Aborting processing file: {csv_path}"
        )

    def search_in_csv(
        self,
        csv_content,
        value_to_search,
        searchable_columns=None,
        return_the_first_match=False,
    ):
        """
        Read CSV and search for value in the content
        :param csv_content: {pandas.core.frame.DataFrame}
        :param value_to_search: {str} of value to search for
        :param searchable_columns: {list} List of columns names
        :param return_the_first_match: {bool} return first matching row
        :return: {list} list of CSVItems
        """
        date_frame = csv_content.applymap(get_value_for_search)
        date_frame = date_frame.applymap(str)

        if searchable_columns:
            searchable_columns = list(
                set(searchable_columns).intersection(date_frame.columns)
            )
            date_frame = date_frame[
                date_frame[searchable_columns].apply(
                    lambda x: value_to_search in list(map(str, x)), axis=1
                )
            ]
        else:
            date_frame = date_frame.loc[date_frame.eq(value_to_search).any(axis=1)]

        if return_the_first_match:
            date_frame = date_frame.head(1)

        return [
            CSVItem(single_raw.to_dict()) for _, single_raw in date_frame.iterrows()
        ]

    def save_json_to_csv(
        self,
        json_string: str,
        file_path: str,
        overwrite: bool = False,
        vertical_unpacking: bool = False,
    ) -> dict[str, str]:
        """Save a JSON string to a CSV file.

        This function parses a JSON string, flattens it (either vertically
        or standard wide format), and writes it to the specified CSV path.

        Args:
            json_string: The JSON string to convert.
            file_path: Destination file path.
            overwrite: Whether to overwrite existing file. Defaults to False.
            vertical_unpacking: If True, applies vertical flattening. Defaults to False.

        Returns:
            A dictionary with the final CSV file path.
        """
        resolved_path = get_file_path(file_path=file_path, overwrite=overwrite)
        json_data = self._parse_json(json_string)
        flat_data: list[dict[str, Any]]

        if vertical_unpacking:
            self.siemplify.LOGGER.info("Using vertical unpacking for CSV conversion.")
            flat_data = flatten_json_vertically(json_data)
        else:
            self.siemplify.LOGGER.info("Using standard (wide) logic for CSV conversion.")
            if not json_data:
                flat_data = []
            elif isinstance(json_data, list):
                flat_data = [dict_to_flat(elem) for elem in json_data]
            else:
                flat_data = [dict_to_flat(json_data)]

        if not flat_data:
            self.siemplify.LOGGER.warning("No data found to write to CSV.")
            flat_data = []

        csv_data = construct_csv(flat_data)
        self._write_csv_file(resolved_path, csv_data)

        self.siemplify.LOGGER.info(f"CSV successfully written to {resolved_path}")
        return {"filepath": resolved_path}

    def _parse_json(self, json_string: str) -> Any:
        """Parse JSON string safely."""
        try:
            return json.loads(json_string)

        except json.JSONDecodeError as error:
            raise CSVJsonIsInvalidError("The JSON structure is invalid.") from error

    def _write_csv_file(self, file_path: str, csv_data: list[str]) -> None:
        """Write flattened data to CSV file line-by-line."""
        try:
            with open(file_path, "w", encoding="utf-8", newline="") as csv_handler:
                final_content = "\n".join(csv_data) + "\n"
                csv_handler.write(final_content)

        except OSError as error:
            self.siemplify.LOGGER.error(f"Failed to write CSV file: {error}")
            raise
