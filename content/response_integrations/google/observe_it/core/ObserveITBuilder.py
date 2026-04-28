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
import re

from .ObserveITDatamodels import Alert


class ObserveITBuilder:
    def build_alert(self, alert_data):
        # type: (dict) -> Alert
        """
        Build alert from response dict
        @param alert_data: Response dict
        @return: Alert
        """
        return Alert(raw_data=alert_data, **self._change_param_names(alert_data))

    def _change_param_names(self, data):
        # type: (dict) -> dict
        """
        Convert all camel keys in dict to snake one
        @param data: dictionary with camel case keys
        @return: dictionary with snake case keys
        """
        return {
            self._covert_camel_to_snake(key): value for key, value in list(data.items())
        }

    @staticmethod
    def _covert_camel_to_snake(camel):
        # type: (str or unicode) -> str or unicode
        """
        Converts camel case to snake
        @param camel: Camel case string
        @return: Snake case string
        """
        camel = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", camel)
        return re.sub("([a-z0-9])([A-Z])", r"\1_\2", camel).lower().replace("__", "_")
