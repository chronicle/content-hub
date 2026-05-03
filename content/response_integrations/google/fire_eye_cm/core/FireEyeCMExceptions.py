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
class FireEyeCMException(Exception):
    pass


class IncorrectHashTypeException(FireEyeCMException):
    pass


class FireEyeCMUnsuccessfulOperationError(FireEyeCMException):
    """
    Unsuccessful operation in FireEye CM
    """

    pass


class FireEyeCMSensorApplianceNotFound(FireEyeCMException):
    """
    Sensor appliance wasn't found Exception in FireEye CM
    """

    pass


class FireEyeCMNotFoundException(FireEyeCMException):
    """
    Not Found Exception in FireEye CM
    """

    pass


class FireEyeCMValidationException(FireEyeCMException):
    """
    Validation Exception for FireEye CM
    """

    pass


class FireEyeCMDownloadFileError(FireEyeCMException):
    """
    Unsuccessful download of a file exception for FireEye CM
    """

    pass
