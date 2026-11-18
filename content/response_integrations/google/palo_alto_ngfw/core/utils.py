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

def normalize_string(text: str) -> str:
    """Normalize a string by replacing non-alphanumeric characters with underscores.

    - Replace all non-alphanumeric characters with an underscore
    - Compress multiple consecutive underscores into one
    - Convert to lowercase
    - Strip leading/trailing underscores

    :param text: String to normalize
    :return: Normalized string
    """
    if text:
        # Replace all non-alphanumeric characters with an underscore
        text = re.sub(r'[^a-zA-Z0-9]', '_', text.lower())
        # Compress multiple consecutive underscores into one
        return re.sub(r'_+', '_', text).strip('_')
    return text
