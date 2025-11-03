from __future__ import annotations


class Config:
    VERSION: str = "Google-SecOps:1.0"
    INTEGRATION_NAME: str = "ANYRUN-TI-Feeds"
    DATE_TIME_FORMAT: str = "%Y-%m-%d %H:%M:%S"

    TAXII_DATATABLES: dict[str, str] = {
        "ip": "anyrun_feed_ip",
        "url": "anyrun_feed_url",
        "domain": "anyrun_feed_domain",
    }
