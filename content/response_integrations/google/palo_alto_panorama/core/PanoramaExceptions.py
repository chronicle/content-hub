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
class PanoramaException(Exception):
    """
    Common Panorama Exception
    """

    pass


class ResponseObjectNotSet(PanoramaException):
    """
    Exception if response object if None
    """

    pass


class JobNotFinishedException(PanoramaException):
    """
    Exception if job not completed yet
    """

    def __init__(self, progress):
        super(JobNotFinishedException, self).__init__()
        self.progress = progress


class PanoramaConnectivityException(PanoramaException):
    pass


class PanoramaAuthorizationException(PanoramaException):
    pass


class PanoramaAlertsException(PanoramaException):
    pass


class PanoramaSeverityException(PanoramaException):
    pass
