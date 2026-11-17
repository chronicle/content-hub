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
class VertexAIException(Exception):
    """General exception for Vertex AI."""


class VertexAIValidationException(VertexAIException):
    """General exception for validation errors."""


class VertexAIManagerException(VertexAIException):
    """General exception for Vertex AI API Manager."""


class VertexAIAuthException(VertexAIException):
    """Exception in case of authentication error."""


class VertexAIInvalidJsonException(VertexAIException):
    """Exception in case of invalid JSON string provided."""
