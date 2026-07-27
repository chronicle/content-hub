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
