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
import abc

from google_forms.core.datamodels import AlertResponse, FormResponse
from google_forms.tests.common import MOCK_DATA


class GoogleForms(abc.ABC):

    def list_users(self) -> dict:
        return MOCK_DATA.get("connectivity")

    def add_user(self):
        return self.list_users

    def get_forms(self) -> AlertResponse:
        return MOCK_DATA.get("get_forms")

    def get_form_details(self) -> FormResponse:
        return FormResponse.from_json(MOCK_DATA.get("get_form_details"))
