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
class TrendVisionOneException(Exception):
    """General exception for TrendVisionOne."""

    def __init__(self, *args: object, error_type: str | None = None) -> None:
        """Init the exception.

        Args:
            *args: The exception message arguments.
            error_type: The failure reason, if the code that raises the exception knows it.

        """
        super().__init__(*args)
        self.error_type = error_type


class TrendVisionOneTimeoutException(TrendVisionOneException):
    """
    General exception in case of timeouts for TrendVisionOne
    """

    pass
