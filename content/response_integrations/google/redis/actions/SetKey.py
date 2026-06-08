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


@output_handler
def main():
    siemplify = SiemplifyAction()
    conf = siemplify.get_configuration("Redis")
    server = conf["Server Address"]
    port = int(conf["Port"])

    redis_manager = RedisManager(server, port, 0)
    # Strings are the most basic kind of Redis value.
    # Redis Strings are binary safe, this means that a Redis string can contain any kind of data
    key = siemplify.parameters["Key Name"]
    value = siemplify.parameters["Value"]

    is_set = redis_manager.set_key(key, value)

    # output_message = "Successfully set {value} to {key}.".format(value=value, key=key)
    output_message = "Successfully set value to key"
    siemplify.end(output_message, "true")


if __name__ == "__main__":
    main()
