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
class NmapManagerError(Exception):
    """General Error For Nmap."""


class NmapNotFoundError(NmapManagerError):
    """Not Found Error For Nmap."""


class NmapValidationError(NmapManagerError):
    """Validation Error For Nmap."""


class NmapNoValidConnectionsError(NmapManagerError):
    """No Valid Connections Error For Nmap."""


class NmapScanError(NmapManagerError):
    """Scan Error For Nmap."""
