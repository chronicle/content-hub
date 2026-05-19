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
from .datamodels import (
    DomainReputation,
    EmailInformation,
    IPReputation,
    Screenshot,
    URLReputation,
)


class APIVoidTranslationLayer:
    @staticmethod
    def build_ip_reputation_obj(raw_data):
        return IPReputation(raw_data)

    @staticmethod
    def build_domain_reputation_obj(raw_data):
        return DomainReputation(raw_data)

    @staticmethod
    def build_url_reputation_obj(raw_data):
        return URLReputation(raw_data)

    @staticmethod
    def build_screenshot_obj(raw_data):
        return Screenshot(raw_data, **raw_data)

    @staticmethod
    def build_email_information_obj(raw_data):
        return EmailInformation(raw_data, **raw_data)
