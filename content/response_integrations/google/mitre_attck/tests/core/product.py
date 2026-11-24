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
