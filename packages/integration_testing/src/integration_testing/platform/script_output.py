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

from __future__ import annotations

import dataclasses
import io
import json
from typing import TYPE_CHECKING, Self

from TIPCommon.base.data_models import ActionOutput, ConnectorOutput

if TYPE_CHECKING:
    from types import TracebackType

    from TIPCommon.types import SingleJson


@dataclasses.dataclass(slots=True)
class MockActionOutput:
    _out: io.StringIO = dataclasses.field(default_factory=io.StringIO)
    _err: io.StringIO = dataclasses.field(default_factory=io.StringIO)

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        self.flush()

    @property
    def results(self) -> ActionOutput | None:
        """Get the action's output results."""
        if not self._out.getvalue():
            return None

        output_json: SingleJson = json.loads(self._out.getvalue())
        return ActionOutput.from_json(output_json)

    @property
    def errors(self) -> str:
        return self._err.getvalue()

    def flush(self) -> None:
        self._out.truncate(0)
        self._out.seek(0)
        self._err.truncate(0)
        self._err.seek(0)

    def get_out_io(self) -> io.StringIO:
        return self._out

    def get_err_io(self) -> io.StringIO:
        return self._err


class MockConnectorOutput:
    __slots__: tuple[str] = ("_err", "_out")

    def __init__(self) -> None:
        self._out: io.StringIO = io.StringIO()
        self._err: io.StringIO = io.StringIO()

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        self.flush()

    @property
    def results(self) -> ConnectorOutput | None:
        """Get the connector's output results."""
        if not self._out.getvalue():
            return None

        output_json: SingleJson = json.loads(self._out.getvalue())
        return ConnectorOutput.from_json(output_json)

    @property
    def errors(self) -> str:
        return self._err.getvalue()

    def flush(self) -> None:
        self._out.truncate(0)
        self._out.seek(0)
        self._err.truncate(0)
        self._err.seek(0)

    def get_out_io(self) -> io.StringIO:
        return self._out

    def get_err_io(self) -> io.StringIO:
        return self._err
