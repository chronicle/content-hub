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
class Breach:
    def __init__(self, raw_data=None, domain=None, breach_date=None):
        self.raw_data = raw_data
        self.domain = domain
        self.breach_date = breach_date

    def as_csv(self):
        """
        Get the account breaches data as csv table data
        :return: {list} The csv data
        """
        return {"Domain": self.domain, "Date": self.breach_date}


class Paste:
    def __init__(
        self, raw_data=None, title=None, date=None, email_count=None, source=None
    ):
        self.raw_data = raw_data
        self.title = title
        self.date = date
        self.email_count = email_count
        self.source = source

    def as_csv(self):
        """
        Get the account pastes data as csv table data
        :return: {list} The csv data
        """
        return {
            "Title": self.title,
            "Date": self.date,
            "Emails": self.email_count,
            "Source": self.source,
        }
