"""Defines an abstract interface for components that can be restructured.

This module introduces the `Restructurable` abstract base class. Any class
that needs to perform a restructuring operation should implement this
interface by providing a concrete implementation for the `restructure` method.
"""

# Copyright 2025 Google LLC
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


class Restructurable(abc.ABC):
    @abc.abstractmethod
    def restructure(self) -> None:
        """Restructure the component."""
