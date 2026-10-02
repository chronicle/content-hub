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
class HTTPV2Exception(Exception):
    """General exception for HTTP V2"""


class HTTPV2AuthException(HTTPV2Exception):
    """Exception in case of authentication error"""


class HTTPV2CertificateException(HTTPV2Exception):
    """Exception in case of certificate error"""


class HTTPV2HTTPException(HTTPV2Exception):
    """Exception in case of HTTP error"""

    def __init__(self, message, status_code=None):
        super().__init__(message)
        self.status_code = status_code


class HTTPV2FileException(HTTPV2Exception):
    """Exception in case of file related error"""


class HTTPV2DomainMismatchException(HTTPV2Exception):
    """Exception when restrict domain is on and the request uses not allowed domain."""
