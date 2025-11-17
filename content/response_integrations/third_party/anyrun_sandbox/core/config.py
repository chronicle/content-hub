from __future__ import annotations


class Config:
    """The main configuration class"""

    VERSION: str = "Google-SecOps:1.0"
    INTEGRATION_NAME: str = "ANYRUN-Sandbox"
    DATE_TIME_FORMAT: str = "%Y-%m-%d %H:%M:%S"

    SANDBOX_DATATABLE: str = "anyrun_sandbox_iocs"
