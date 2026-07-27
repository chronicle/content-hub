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
from ..core.MongoDBManager import MongoDBManager


@output_handler
def main():
    siemplify = SiemplifyAction()
    conf = siemplify.get_configuration("MongoDB")
    server = conf["Server Address"]
    username = conf["Username"]
    password = conf["Password"]
    port = int(conf["Port"])
    is_authenticate = conf["Use Authentication"].lower() == "true"

    mongodb_manager = MongoDBManager(
        username=username,
        password=password,
        server=server,
        port=port,
        is_authenticate=is_authenticate,
    )

    # Check if the connection is established or not.
    mongodb_manager.test_connectivity()

    # If no exception occur - then connection is successful
    output_message = f"Successfully connected to MongoDB at {server}:{port}."
    siemplify.end(output_message, True)


if __name__ == "__main__":
    main()
