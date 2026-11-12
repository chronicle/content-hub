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

import importlib

from nessus_scanner.tests import common


def test_imports() -> None:
    integration_name = common.INTEGRATION_PATH.name
    for subdir in ("core", "actions", "connectors", "jobs"):
        folder = common.INTEGRATION_PATH / subdir
        if not folder.is_dir():
            continue
        for py_file in folder.rglob("*.py"):
            if py_file.stem == "__init__":
                continue
            rel = py_file.relative_to(common.INTEGRATION_PATH).with_suffix("")
            mod_name = ".".join((integration_name, *rel.parts))
            importlib.import_module(mod_name)
