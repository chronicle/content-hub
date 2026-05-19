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
from .CBResponseManager import CBResponseManager
from .CBResponseManager6_3 import CBResponseManager6_3
from .CBResponseManager5_1 import CBResponseManager5_1


class CBResponseManagerLoader:
    @staticmethod
    def load_manager(version, *args, **kwargs):
        if version >= 6.3:
            return CBResponseManager6_3(*args, **kwargs)
        elif version == 5.1:
            return CBResponseManager5_1(*args, **kwargs)
        else:
            return CBResponseManager(*args, **kwargs)
