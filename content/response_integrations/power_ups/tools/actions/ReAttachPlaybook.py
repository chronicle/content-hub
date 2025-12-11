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

import psycopg2
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from TIPCommon.rest.soar_api import get_integration_instance_details_by_name

INSTANCE_NAME = "Siemplify"
SHARED_ENV = "*"
GET_WFS_QUERY = """
select * from "WorkflowInstances" where "WorkflowName" = '{}' AND "CaseId" = {}
"""

DELETE_WI_QUERY = (
    "delete from \"WorkflowInstances\" "
    "where \"CaseId\" = {} "
    "and \"WorkflowName\" = '{}' "
    "and \"IndicatorIdentifier\" = '{}';"
)

DELETE_AR_QUERY = (
    "delete from \"ActionResults\" "
    "where \"CaseId\" = {} "
    "and \"WorkflowId\" = '{}' "
    "and \"IndicatorIdentifier\" = '{}';"
)
ADD_PLAYBOOK_URL = "{}/external/v1/playbooks/AttacheWorkflowToCase?format=camel"


class ConnectToDb:
    def __init__(self, server, username, password, database, port=5432):
        self.username = username
        self.password = password
        self.server = server
        self.database = database
        self.port = port

        # Connect to PostgreSQL
        self.conn = psycopg2.connect(
            f"dbname='{self.database}' user='{self.username}' "
            f"host='{self.server}' password='{self.password}'",
        )

    def execute(self, query):
        """Execute a query on PostgresSQL database and get results.
        :param query: {str} SQL query like 'SELECT * FROM exampleDB'
        :return: {list} JSON like results
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute(query)
            self.conn.commit()

            if cursor.description:
                # Fetch column names
                columns = [column[0] for column in cursor.description]

                # Fetch rows
                rows = cursor.fetchall()
                # raise Exception(rows)

                # Construct results
                data = self.get_data(rows, columns)
                return data
        except Exception as e:
            # Query failed - rollback.
            self.conn.rollback()
            raise Exception(e)

    def close(self):
        """Close the connection"""
        self.conn.close()

    @staticmethod
    def get_data(rows, columns):
        """Converts list of rows to JSON like format.
        :param rows: {list} Data rows from PostgresSQL DB.
        :param columns: {list} Column names from PostgresSQL DB;
        :return: {list} JSON like formatted data from query.
        """
        data = []
        for row in rows:
            temp = {column: value for column, value in zip(columns, row, strict=False)}
            data.append(temp)

        return data


def get_integration_instance(siemplify, integration_name, environment, instance_name):
    filtered = get_integration_instance_details_by_name(
        chronicle_soar=siemplify,
        integration_identifier=integration_name,
        instance_display_name=instance_name,
        environments=[environment],
    )
    return filtered if filtered else {"identifier": "N/A"}


@output_handler
def main():
    siemplify = SiemplifyAction()
    playbook_name = siemplify.extract_action_param("Playbook Name", print_value=True)
    instance_id = get_integration_instance(
        siemplify,
        "PostgreSQL",
        SHARED_ENV,
        INSTANCE_NAME,
    )["identifier"]
    if instance_id == "N/A":
        siemplify.end(
            "Please configure the Siemplify instance of the PostgreSQL integration.",
            "Please configure the Siemplify instance of the PostgresSQL integration.",
        )
    conf = super(SiemplifyAction, siemplify).get_configuration(
        "PostgreSQL",
        SHARED_ENV,
        instance_id,
    )
    server_addr = conf["Server Address"]
    username = conf["Username"]
    password = conf["Password"]
    port = conf.get("Port")
    orch_mgr = ConnectToDb(
        username=username,
        password=password,
        server=server_addr,
        database="siemplify_orchestration_db",
        port=port,
    )
    sys_mgr = ConnectToDb(
        username=username,
        password=password,
        server=server_addr,
        database="siemplify_system_db",
        port=port,
    )
    try:
        res = (
            orch_mgr.execute(GET_WFS_QUERY.format(playbook_name, siemplify.case_id))
            or []
        )
        case = siemplify._get_case()
        for attached_wf in res:
            wf_id = attached_wf["WorkflowDefinitionIdentifier"]
            orch_mgr.execute(
                DELETE_WI_QUERY.format(
                    siemplify.case_id,
                    playbook_name,
                    attached_wf["IndicatorIdentifier"],
                ),
            )
            sys_mgr.execute(
                DELETE_AR_QUERY.format(
                    siemplify.case_id,
                    wf_id,
                    attached_wf["IndicatorIdentifier"],
                ),
            )
            alert = list(
                filter(
                    lambda x: x["alert_group_identifier"]
                    == attached_wf["IndicatorIdentifier"],
                    case["cyber_alerts"],
                ),
            )[0]
            payload = {
                "cyberCaseId": siemplify.case_id,
                "alertGroupIdentifier": attached_wf["IndicatorIdentifier"],
                "alertIdentifier": alert["identifier"],
                "shouldRunAutomatic": True,
                "wfName": playbook_name,
            }
            res2 = siemplify.session.post(
                ADD_PLAYBOOK_URL.format(siemplify.API_ROOT),
                json=payload,
            )
            res2.raise_for_status()
    except Exception as err:
        siemplify.LOGGER.error("Error re-running the playbook.")
        siemplify.LOGGER.exception(err)

    status = EXECUTION_STATE_COMPLETED
    output_message = "Successfully re-attached the playbook to the case."
    result_value = (
        True  # Set a simple result value, used for playbook if\else and placeholders.
    )
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  result_value: {result_value}\n  "
        f"output_message: {output_message}",
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
