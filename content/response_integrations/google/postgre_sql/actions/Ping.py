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
from ..core.PostgreSQLManager import PostgreSQLManager


@output_handler
def main():
    siemplify = SiemplifyAction()
    conf = siemplify.get_configuration("PostgreSQL")
    server_addr = conf["Server Address"]
    username = conf["Username"]
    password = conf["Password"]
    port = conf.get("Port")
    database = conf.get("Database Name For Testing")

    postgres_manager = PostgreSQLManager(
        username=username,
        password=password,
        server=server_addr,
        database=database,
        port=port,
    )

    postgres_manager.close()

    # If no exception occur - then connection is successful
    output_message = f"Successfully connected to {database} at {server_addr}:{port}."
    siemplify.end(output_message, True)


if __name__ == "__main__":
    main()
