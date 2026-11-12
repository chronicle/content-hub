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
import abc

import dataclasses
from typing import Iterator, Any


@dataclasses.dataclass
class CSV(abc.ABC):
    """
    Mock product simulating a file system for CSV integration.
    """
    files: dict[str, str] = dataclasses.field(default_factory=dict)

    def mock_open(
        self, file_path: str, _mode: str = "r", **_kwargs
    ) -> _MockFileHandle:
        """
        Returns a mock file handle to simulate file operations.
        """
        return _MockFileHandle(file_path, self)

    def append_content_to_file(self, file_path: str, content: str) -> None:
        """Appends content to the given file path in the mock file system."""
        if file_path not in self.files:
            self.files[file_path] = ""
        self.files[file_path] += content

    def get_written_content(self, file_path: str) -> str | None:
        """Retrieves the content of a file for test verification."""
        return self.files.get(file_path)


class _MockFileHandle:
    """Mock file handle managed by the CSV file system mock."""

    def __init__(self, file_path: str, file_system: CSV) -> None:
        self.file_path: str = file_path
        self.file_system: CSV = file_system
        self._line_iterator: Iterator[str] | None = None

        self._initialize_sdk_config_if_needed()

    def _initialize_sdk_config_if_needed(self) -> None:
        """
        Provides a minimal configuration for SDK if sdk_config.ini is
        requested.
        """
        if "sdk_config.ini" in self.file_path:
            self._line_iterator = iter(
                [
                    "[ExecutionConfig]\n",
                    "runFolderPath = /tmp\n",
                ]
            )

    def __enter__(self) -> _MockFileHandle:
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        pass

    def write(self, content: str) -> None:
        self.file_system.append_content_to_file(self.file_path, content)

    def __iter__(self) -> Iterator[str]:
        """Returns the internal line iterator or an empty iterator if none
        is set.
        """
        if self._line_iterator:
            return self._line_iterator
        return iter([])
