from __future__ import annotations
from .datamodels import *


class ServiceDeskPlusV3Parser:

    def build_universal_object(self, raw_data):

        return APIResponse(raw_data=raw_data)

    def build_note_object(self, raw_data):

        return Note(
            raw_data=raw_data,
            notes=raw_data.get("notes"),
            note_ids=[note_data.get("id") for note_data in raw_data.get("notes", [])],
        )

    def build_request_object(self, raw_data):

        return Request(
            raw_data=raw_data,
            status=raw_data.get("request", {}).get("status", {}).get("name"),
            orig_request=raw_data.get("request", {}),
        )
