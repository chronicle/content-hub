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


class HashiCorpVaultParser:
    @staticmethod
    def build_key_value_response_object(raw_data):
        return KeyValueResponse(
            raw_data=raw_data, keys=raw_data.get("data", {}).get("keys", [])
        )

    @staticmethod
    def build_generic_response_object(raw_data):
        return GenericResponse(raw_data=raw_data, data=raw_data.get("data"))
