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

# ruff:file-ignore[non-empty-init-module]

import importlib
import os
import sys

# Re-route third-party package attributes to prevent shadowing.
# When python loads the local 'akeyless' package, we temporarily clean sys.path of local
# paths, load the real third-party 'akeyless' SDK package, and inject its contents here.
_original_path = sys.path.copy()

try:
    sys.path = [
        p
        for p in sys.path
        if not os.path.normpath(p).endswith(os.path.normpath("response_integrations/google/akeyless"))
        and not os.path.normpath(p).endswith(os.path.normpath("response_integrations/google"))
    ]
    # Remove from sys.modules to force loading the third-party library
    _old_module = sys.modules.pop("akeyless", None)
    _real_akeyless = importlib.import_module("akeyless")

    # Expose the third-party library attributes
    for _attr in dir(_real_akeyless):
        if not _attr.startswith("__"):
            globals()[_attr] = getattr(_real_akeyless, _attr)
finally:
    sys.path = _original_path
    if "_old_module" in locals() and _old_module is not None:
        sys.modules["akeyless"] = _old_module
