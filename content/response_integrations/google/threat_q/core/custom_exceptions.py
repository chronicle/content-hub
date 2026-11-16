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
class ThreatQManagerException(Exception):
    pass


class ObjectNotFoundException(ThreatQManagerException):
    pass


class LinkObjectsException(ThreatQManagerException):
    pass


class ListRelatedObjectsException(ThreatQManagerException):
    pass


class MalwareDetailsException(ThreatQManagerException):
    pass


class MalwareDetailsNotFoundException(ThreatQManagerException):
    pass


class SourceObjectNotFoundException(ObjectNotFoundException):
    pass


class DestinationObjectNotFoundException(ObjectNotFoundException):
    pass


class RelatedObjectNotFoundException(ObjectNotFoundException):
    pass


class ObjectCreateException(ThreatQManagerException):
    pass


class EventCreateException(ThreatQManagerException):
    pass


class IndicatorScoreException(ThreatQManagerException):
    pass


class InvalidFieldException(ThreatQManagerException):
    pass
