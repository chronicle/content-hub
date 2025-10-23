from __future__ import annotations


class Config:
    VERSION: str = "Google-SecOps:1.0"
    INTEGRATION_NAME: str = "ANYRUN-TI-Lookup"

    ENTITIES: dict[str, str] = {
        "address": "destination_ip",
        "ipset": "destination_ip",
        "destinationurl": "url",
        "domain": "domain_name",
        "process": "image_path",
        "filehash": "query",
    }
