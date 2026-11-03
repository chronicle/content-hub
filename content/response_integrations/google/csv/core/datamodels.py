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
from chardet import detect

NULL_VALUE = '""'


class CSVItem:
    def __init__(self, raw_data):
        self.additional_data = {}
        self.raw_data = raw_data
        self.column_filter = []
        self.processed_raw_data = {}
        self.is_data_processed = False
        self.filtered_data_exist = True

    @staticmethod
    def replace_spaces_with_underscore(value):
        """
        Remove spaces from string
        :param value: {str}
        :return: {str} string with underscores instead of spaces
        """
        return value.replace(" ", "_")

    @staticmethod
    def decode_param(param):
        """
        A function that normalizes the param, values from the CSV file.
        It solves the problem with encodings which we encountered with non-ASCII characters.
        :param param {str} key or value that should be normalized
        return {str} converted parameter
        """
        try:
            if not isinstance(param, bytes):
                return str(param)
            current_encoding = detect(param)["encoding"]
            return param.decode(current_encoding if current_encoding else "UTF-8")
        except Exception as e:
            raise Exception(f"Failed to prepare the params for entity enrichment: {e}")

    @staticmethod
    def is_nullable_value(value):
        return value == NULL_VALUE

    def add_additional_data(self):
        if self.additional_data:
            self.processed_raw_data.update(self.additional_data)

    def apply_column_filter(self):
        if self.column_filter:
            filtered_data = {
                column: value
                for column, value in self.raw_data.items()
                if column in self.column_filter
            }
            if filtered_data:
                self.processed_raw_data = filtered_data
            else:
                self.filtered_data_exist = False

    def decode_data(self):
        decoded_raw_data = {}
        for key, value in self.processed_raw_data.items():
            decoded_key = self.decode_param(key)
            decoded_value = (
                value
                if self.is_nullable_value(value)
                else self.decode_param(value[0] if isinstance(value, list) else value)
            )
            decoded_raw_data[decoded_key] = decoded_value
        self.processed_raw_data = decoded_raw_data

    def get_process_data(self):
        if not self.is_data_processed:
            self.processed_raw_data = self.raw_data
            self.add_additional_data()
            self.apply_column_filter()
            self.decode_data()
            self.is_data_processed = True

        return self.processed_raw_data

    def to_csv(self):
        return self.get_process_data()

    def to_json(self):
        return {
            self.replace_spaces_with_underscore(key): value
            for key, value in self.get_process_data().items()
        }

    def get_enrichment_data(self):
        return self.get_process_data()
