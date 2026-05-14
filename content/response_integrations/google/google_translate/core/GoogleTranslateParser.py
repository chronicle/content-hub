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
