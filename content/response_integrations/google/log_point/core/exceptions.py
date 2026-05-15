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
class LogPointApiException(Exception):
    """
    LogPoint API exception
    """

    pass


class LogPointCredentialsException(Exception):
    """
    LogPoint API exception
    """

    pass


class LogPointInvalidParametersException(Exception):
    """
    LogPoint API exception
    """


class LogPointNotFoundException(Exception):
    """
    LogPoint Not Found exception
    """

    pass


class LogPointTimeoutException(Exception):
    """
    LogPoint Timeout exception
    """


class LogPoIntInsufficientEntityTypesException(Exception):
    """
    LogPoint Insufficient entity types exception
    """

    pass


class LogPointUnsuccessfulQueryResultsException(Exception):
    """
    LogPoint Unsuccessful query results exception
    """

    pass
