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
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifySdkConfig import SiemplifySdkConfig
from ..core.RunnersManager import RunnersManagerBuilder, PermissionError


@output_handler
def main():
    siemplify = SiemplifyAction()
    command = siemplify.parameters["Command"]
    username = siemplify.parameters["Username"]
    password = siemplify.parameters["Password"]
    domain = siemplify.parameters.get("Domain")
    daemon = siemplify.parameters["Daemon"].lower() == "true"

    run_as_manager = RunnersManagerBuilder.create_manager(SiemplifySdkConfig.is_linux())
    try:
        return_code, stdout, stderr = run_as_manager.run_command_as_user(
            command, username, domain, password, daemon
        )
    except PermissionError as e:
        raise e
    except Exception as e:
        raise e

    if return_code:
        siemplify.end(stderr, "false")

    siemplify.end(stdout, "true")


if __name__ == "__main__":
    main()
