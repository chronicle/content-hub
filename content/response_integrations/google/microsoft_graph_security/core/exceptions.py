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
class MicrosoftGraphSecurityFileNotFound(Exception):
    """File not found exception for microsoft graph security"""


class ActionParameterValidationError(Exception):
    """Generic error for parameters validation error inside action body"""


class MicrosoftGraphSecurityManagerError(Exception):
    """ General Exception for microsoft graph security manager"""


class IncidentNotFoundException(Exception):
    """Exception when Incident not found."""


class AlertNotFoundException(Exception):
    """Exception when Alert not found."""
