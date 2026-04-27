from __future__ import annotations
from .datamodels import *


class GoogleTranslateParser:
    def build_languages_list(self, raw_json):
        return [
            self.build_language_object(item)
            for item in raw_json.get("data", {}).get("languages", [])
        ]

    @staticmethod
    def build_language_object(raw_data):
        return Language(raw_data=raw_data, name=raw_data.get("language"))
