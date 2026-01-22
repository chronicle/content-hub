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

import functools
import inspect
from typing import Any, Callable


def main(class_: Callable[[], Any]) -> Callable[[], Any]:
    @functools.wraps(class_)
    def do_main() -> Any:
        if not inspect.isclass(class_):
            raise TypeError("The main decorator supports classes only")

        if callable(class_) and hasattr(class_, "run") and callable(class_.run):
            class_().run()

        elif callable(class_) and hasattr(class_, "start") and callable(class_.start):
            class_().start()

        else:
            raise RuntimeError("Could not run script using 'run' or 'start' methods")

    if __name__ == "__main__":
        do_main()

    return class_
