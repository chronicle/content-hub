from __future__ import annotations
from .datamodels import *


class CylanceParser:

    def build_download_link_object(self, raw_data):
        return DownloadLink(raw_data=raw_data, url=raw_data.get("url", ""))
