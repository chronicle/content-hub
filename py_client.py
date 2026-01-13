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

import json
from pathlib import Path
from typing import Any

import requests


class Backend:
    def __init__(self, api_root: str, app_key: str) -> None:
        self.base_url: str = f"{api_root}/api/external/v1"
        self.session: requests.Session = requests.Session()
        self.session.headers.update({"AppKey": app_key})

    def get_connector_instances(self) -> dict[str, Any]:
        url: str = f"{self.base_url}/connectors/GetConnectorsData"
        response: requests.Response = self.session.get(url)
        response.raise_for_status()
        return response.json()


def main() -> None:
    backend: Backend = Backend(
        api_root="https://ao4tp.siemplify-soar.com",
        app_key="QYOVasxx3MTZEjsdth2dYRXiCgCPIl/U1I6e6XD6vMM=",
    )
    instances: dict[str, Any] = backend.get_connector_instances()
    (Path(__file__).parent / "connectors.json").write_text(
        json.dumps(instances, indent=4, sort_keys=True), encoding="utf"
    )


if __name__ == "__main__":
    main()
