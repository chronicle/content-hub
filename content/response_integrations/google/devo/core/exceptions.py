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
class DevoManagerError(Exception):
    """
    General Exception for Devo Manager Error
    """

    pass


class DevoManagerErrorValidationException(Exception):
    """
    Validation Exception for Devo Manager Error
    """

    pass


class DevoManagerErrorUnauthorizedException(Exception):
    """
    Unauthorized Exception for Devo Manager Error
    """

    pass


class DevoManagerErrorBadQueryException(Exception):
    """
    Bad Query Exception for Devo Manager Error
    """

    pass
