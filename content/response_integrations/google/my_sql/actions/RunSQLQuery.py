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
from ..core.MySQLManager import MySQLManager
import json
import datetime


def datetime_handler(x):
    if isinstance(x, datetime.datetime):
        return x.isoformat()


@output_handler
def main():
    siemplify = SiemplifyAction()
    conf = siemplify.get_configuration("MySQL")
    server_addr = conf["Server Address"]
    username = conf["Username"]
    password = conf["Password"]
    port = int(conf.get("Port"))

    database = siemplify.parameters["Database Name"]
    query = siemplify.parameters["Query"]

    mysql_manager = MySQLManager(
        username=username,
        password=password,
        server=server_addr,
        database=database,
        port=port,
    )

    # Run search query
    results = mysql_manager.execute(query) or []

    # Close the connection
    mysql_manager.close()

    if results:
        # Construct csv
        csv_output = mysql_manager.construct_csv(results)
        siemplify.result.add_data_table("MySQL Query Results", csv_output)

    siemplify.result.add_result_json(json.dumps(results, default=datetime_handler))
    siemplify.end(
        f"Successfully finished search. Found {len(results)} rows.",
        json.dumps(results, default=datetime_handler),
    )


if __name__ == "__main__":
    main()
