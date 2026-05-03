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
from ..core.RedisManager import RedisManager
import json


@output_handler
def main():
    siemplify = SiemplifyAction()
    conf = siemplify.get_configuration("Redis")
    server = conf["Server Address"]
    port = int(conf["Port"])

    redis_manager = RedisManager(server, port, 0)
    key = siemplify.parameters["Key Name"]

    key_value = redis_manager.get_key(key)
    if key_value:
        # output_message = "Key: {key} value is:{value}.".format(value=key_value, key=key)
        output_message = "Find value"
    else:
        # output_message = "Can not find value for {key}.".format(key=key)
        output_message = "Can not find values"
    siemplify.end(output_message, json.dumps(key_value))


if __name__ == "__main__":
    main()
