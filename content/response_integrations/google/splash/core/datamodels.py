# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import annotations
from TIPCommon import dict_to_flat, add_prefix_to_dict
import copy


class BaseModel:
    """
    Base model for inheritance
    """

    def __init__(self, raw_data):
        self.raw_data = raw_data

    def to_json(self):
        return self.raw_data

    def to_csv(self):
        return dict_to_flat(self.to_json())

    def to_enrichment_data(self, prefix=None):
        data = dict_to_flat(self.raw_data)
        return add_prefix_to_dict(data, prefix) if prefix else data


class Address(BaseModel):
    def __init__(self, raw_data, original_url, final_url, title, history, har, png):
        super(Address, self).__init__(raw_data)
        self.original_url = original_url
        self.final_url = final_url
        self.title = title
        self.history = history
        self.har = har
        self.png = png

    def to_json(self):
        json_data = copy.deepcopy(self.raw_data)
        json_data.pop("png", None)
        json_data.pop("html", None)
        return json_data

    def get_enrichment_data(self, include_history, include_har, prefix=None):
        enrichment_data = {
            "original_url": self.original_url,
            "final_url": self.final_url,
            "title": self.title,
            "was_redirected": self.original_url != self.final_url,
        }
        if include_history:
            enrichment_data["has_history"] = len(self.history)
        if include_har:
            enrichment_data["count_har_entries"] = len(
                self.har.get("log", {}).get("entries", [])
            )

        enrichment_data = dict_to_flat(enrichment_data)
        return (
            add_prefix_to_dict(enrichment_data, prefix) if prefix else enrichment_data
        )

    def as_csv(self, include_history, include_har):
        data = self.get_enrichment_data(include_history, include_har)
        return {key: value for key, value in data.items() if value is not None}

    def to_insight(self, include_screenshot):
        content = "<body>"
        content += f'<br><strong>Title:</strong> {self.title or "N/A"}'
        content += f'<br><strong>Final URL:</strong> {self.final_url or "N/A"}<br>'
        if include_screenshot:
            content += f"<br><strong>Screenshot</strong><br><br>"
            content += f'<img src="data:image/jpeg;base64,{self.png}"><br>'
        content += "</body>"
        content += "<p>&nbsp;</p>"

        return content
