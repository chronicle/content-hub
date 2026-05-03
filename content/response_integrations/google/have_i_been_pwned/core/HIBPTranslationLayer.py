from __future__ import annotations
from .datamodels import Breach, Paste


class HIBPTranslationLayer:
    @staticmethod
    def build_breach_obj(raw_data):
        return Breach(
            raw_data=raw_data,
            domain=raw_data.get("Domain"),
            breach_date=raw_data.get("BreachDate"),
        )

    @staticmethod
    def build_paste_obj(raw_data):
        return Paste(
            raw_data=raw_data,
            title=raw_data.get("Title"),
            date=raw_data.get("Date"),
            email_count=raw_data.get("EmailCount"),
            source=raw_data.get("Source"),
        )
