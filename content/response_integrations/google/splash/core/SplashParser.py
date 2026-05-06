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


class SplashParser:
    def build_address_object(self, raw_data):
        return Address(
            raw_data=raw_data,
            original_url=raw_data.get("requestedUrl"),
            final_url=raw_data.get("url"),
            title=raw_data.get("title"),
            history=raw_data.get("history", []),
            har=raw_data.get("har", {}),
            png=raw_data.get("png", ""),
        )
