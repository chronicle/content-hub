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

import contextlib
import dataclasses

from typing import Any


@dataclasses.dataclass(slots=True)
class MitreAttckProduct(abc.ABC):
    """Simulates the MITRE ATT&CK JSON data source returned by the remote endpoint."""

    _attack_data: dict[str, Any] | None = dataclasses.field(default=None)
    _fail_requests_active: bool = dataclasses.field(default=False)

    def set_attack_data(self, data: dict[str, Any]) -> None:
        """Set the STIX bundle that the mock endpoint will return."""
        self._attack_data = data

    def get_attack_data(self) -> dict[str, Any]:
        """Return the stored STIX bundle, raising on simulated failure."""
        if self._fail_requests_active:
            raise RuntimeError("Simulated API failure: unable to fetch MITRE ATT&CK data")
        return self._attack_data or {}

    @contextlib.contextmanager
    def fail_requests(self):
        """Context manager that makes all requests fail with a 500 status."""
        self._fail_requests_active = True
        try:
            yield
        finally:
            self._fail_requests_active = False
