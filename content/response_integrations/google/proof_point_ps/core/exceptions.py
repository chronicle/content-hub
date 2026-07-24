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


class ProofPointPSError(Exception):
    """General exception for ProofPointPS integration."""


class ProofPointPSHTTPError(ProofPointPSError):
    """HTTP-specific exception for ProofPointPS integration."""


class FolderNotFoundError(ProofPointPSError):
    """Exception raised when a quarantine folder does not exist."""


class InvalidParameterError(ProofPointPSError):
    """Invalid parameter exception for ProofPointPS integration."""
