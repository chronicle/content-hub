from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ScanLaunch:
    """The answer to POST /scan/launch."""

    scan_id: str
    status: str
    cached: bool
