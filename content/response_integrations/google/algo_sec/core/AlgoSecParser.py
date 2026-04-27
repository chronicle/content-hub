from __future__ import annotations
from .datamodels import *


class AlgoSecParser:

    def build_request_object(self, raw_data):
        return RequestObject(
            raw_data=raw_data,
            id=raw_data.get("data", {}).get("changeRequestId"),
            redirect_url=raw_data.get("data", {}).get("redirectUrl"),
            status=next(
                (
                    field.get("values", [""])[0]
                    for field in raw_data.get("data", {}).get("fields", [])
                    if field.get("name", "") == "status"
                ),
                "",
            ),
        )

    def build_templates_list(self, raw_data):
        return [self.build_template_object(item) for item in raw_data.get("data", [])]

    def build_template_object(self, raw_data):
        return Template(
            raw_data=raw_data,
            id=raw_data.get("id"),
            name=raw_data.get("name"),
            description=raw_data.get("description"),
            type=raw_data.get("type"),
        )
