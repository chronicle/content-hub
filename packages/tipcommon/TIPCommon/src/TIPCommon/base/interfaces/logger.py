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

import abc
from typing import TypeVar


class Logger(abc.ABC):
    """Logger interface for marketplace scripts.

    Use this interface in places the logger that is passed might be replaced ot mocked
    with a different implementation of this interface.

    Methods:
        - debug()
        - info()
        - warn()
        - error()
        - exception()

    """

    @abc.abstractmethod
    def debug(self, msg: str, *args, **kwargs) -> None:
        pass

    @abc.abstractmethod
    def info(self, msg: str, *args, **kwargs) -> None:
        pass

    @abc.abstractmethod
    def warn(self, warning_msg: str, *args, **kwargs) -> None:
        pass

    @abc.abstractmethod
    def error(self, error_msg: str, *args, **kwargs) -> None:
        pass

    @abc.abstractmethod
    def exception(self, ex: Exception, *args, **kwargs) -> None:
        pass


ScriptLogger = TypeVar("ScriptLogger", bound=Logger)
