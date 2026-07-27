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
class QualysVMManagerError(Exception):
    """
    General Exception for QualysVM manager
    """

    pass


class ScanErrorException(Exception):
    """
    Exception in case of scan error
    """

    pass


class QualysReportFailed(Exception):
    """
    Exception in case a report wasn't found
    """

    pass
