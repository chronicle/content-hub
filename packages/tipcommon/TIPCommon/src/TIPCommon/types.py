# Copyright 2025 Google LLC
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

from typing import (
    Any,
    Callable,
    Collection,
    List,
    Tuple,
    Type,
    TypeVar,
    Union,
)

from collections.abc import MutableMapping

from SiemplifyAction import SiemplifyAction
from SiemplifyConnectors import SiemplifyConnectorExecution
from SiemplifyDataModel import DomainEntityInfo
from SiemplifyJob import SiemplifyJob


_T = TypeVar("_T")
_E = TypeVar("_E")
_R = TypeVar("_R")

ChronicleSOAR = SiemplifyAction | SiemplifyConnectorExecution | SiemplifyJob

Entity = TypeVar("Entity", bound=DomainEntityInfo)

SingleJson = MutableMapping[str, Any]
JSON = Union[SingleJson, List[SingleJson]]
JsonString = TypeVar("JsonString", bound=str)

GeneralFunction = Callable[..., Any]
Contains = Union[_T, Collection[_T], Type[Tuple[_T, ...]], None]

AuthParams = TypeVar("AuthParams")
ApiParams = TypeVar("ApiParams")

Consumer = Callable[[_T], None]
Supplier = Callable[[], _T]
Function = Callable[[_T], _R]
Predicate = Callable[[_T], bool]
UnaryOperator = Callable[[_T], _T]
BiPredicate = Callable[[_T, _E], bool]
BiConsumer = Callable[[_T, _E], None]
BiFunction = Callable[[_T, _E], _R]
BinaryOperator = Callable[[_T, _T], _T]
