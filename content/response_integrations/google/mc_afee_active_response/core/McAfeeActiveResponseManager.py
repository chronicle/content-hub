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

# ============================================================================#
# title           :McAfeeActiveResponse.py
# description     :This Module contain all Jira operations functionality
# author          :victor@siemplify.co
# date            :12-08-2018
# python_version  :2.7 (except 2.7.13 - ctypes bug)
# product_version :1.0
# ============================================================================#

# ============================= IMPORTS ===================================== #
from __future__ import annotations

from dxlclient.broker import Broker
from dxlclient.client import DxlClient
from dxlclient.client_config import DxlClientConfig
from dxlmarclient import (
    ConditionConstants,
    MarClient,
    OperatorConstants,
    ProjectionConstants,
)

# ============================== CONSTS ===================================== #
MAR_COLLECTORS = {
    "CommandLineHistory": ["user", "id"],
    "CurrentFlow": [
        "local_ip",
        "local_port",
        "remote_ip",
        "remote_port",
        "status",
        "process_id",
        "user",
        "user_id",
        "proto",
        "md5",
        "sha1",
    ],
    "DNSCache": ["hostname", "ipaddress"],
    "EnvironmentVariables": ["username", "process_id", "name", "value"],
    "Files": [
        "name",
        "dir",
        "full_name",
        "size",
        "last_write",
        "md5",
        "sha1",
        "created_at",
        "deleted_at",
    ],
    "HostEntries": ["hostname", "ipaddress"],
    "HostInfo": ["hostname", "ip_address", "os"],
    "InstalledCertificates": [
        "issued_to",
        "issued_by",
        "expiration_date",
        "purposes",
        "purposes_extended",
        "friendly_name",
    ],
    "InstalledDrivers": [
        "displayname",
        "description",
        "last_modified_date",
        "name",
        "servicetype",
        "startmode",
        "state",
        "path",
    ],
    "InstalledUpdates": ["description", "hotfix_id", "install_date", "installed_by"],
    "InteractiveSessions": ["userid", "name"],
    "LocalGroups": ["groupname", "groupdomain", "groupdescription", "islocal", "sid"],
    "LoggedInUsers": ["id", "userdomain", "username"],
    "NetworkFlow": [
        "src_ip",
        "src_port",
        "dst_ip",
        "dst_port",
        "time",
        "status",
        "process",
        "process_id",
        "user",
        "user_id",
        "proto",
        "direction",
        "ip_class",
        "seq_number",
        "src_mac",
        "dst_mac",
        "md5",
        "sha1",
    ],  # according to docs also includes 'flags'
    "NetworkInterfaces": [
        "bssid",
        "displayname",
        "gwipaddress",
        "gwmacaddress",
        "ipaddress",
        "ipprefix",
        "macaddress",
        "name",
        "ssid",
        "type",
        "wifisecurity",
    ],
    "NetworkSessions": ["computer", "user", "client", "file", "idletime"],
    "NetworkShares": ["name", "description", "path"],
    "Processes": [
        "name",
        "id",
        "parentname",
        "size",
        "md5",
        "sha1",
        "cmdline",
        "imagepath",
        "kerneltime",
        "usertime",
        "uptime",
        "user",
        "user_id",
    ],  # according to docs also includes 'thread_count', 'parentId'
    "ScheduledTasks": [
        "folder",
        "taskname",
        "status",
        "last_run",
        "username",
        "schedule_on",
    ],  # according to docs also includes 'nextruntime', 'task_run', 'log_on_type'
    "Services": ["description", "name", "startuptype", "status", "user"],
    "Software": ["displayname", "installdate", "publisher", "version"],
    "Startup": ["caption", "command", "description", "name", "user"],
    "UsbConnectedStorageDevices": [
        "vendor_id",
        "product_id",
        "serial_number",
        "device_type",
        "guid",
        "last_connection_time",
        "user_name",
        "last_time_used_by_user",
    ],
    "UserProfiles": [
        "accountdisabled",
        "domain",
        "fullname",
        "installdate",
        "localaccount",
        "lockedout",
        "accountname",
        "sid",
        "passwordexpires",
    ],
    "WinRegistry": ["keypath", "keyvalue", "valuedata", "valuetype"],
}


FILTER_OPERATORS = {
    "GreaterEqualThan": OperatorConstants.GREATER_EQUAL_THAN,
    "GreaterThan": OperatorConstants.GREATER_THAN,
    "LessEqualThan": OperatorConstants.LESS_EQUAL_THAN,
    "LessThan": OperatorConstants.LESS_THAN,
    "Equals": OperatorConstants.EQUALS,
    "Contains": OperatorConstants.CONTAINS,
    "StartWith": OperatorConstants.STARTS_WITH,
    "EndsWith": OperatorConstants.ENDS_WITH,
    "Before": OperatorConstants.BEFORE,
    "After": OperatorConstants.AFTER,
}


# ============================= CLASSES ===================================== #
class McAfeeActiveResponseError(Exception):
    pass


class McAfeeActiveResponseManager:
    def __init__(
        self, broker_urls_list, broker_ca_bundle_path, cert_file_path, private_key_path
    ):
        """:param broker_urls_list: list of brokers urls {list}
        :param broker_ca_bundle_path: broker cert bundle file path {string}
        :param cert_file_path: cert file path {string}
        :param private_key_path: key file path {string}
        """
        # Create config
        config = DxlClientConfig(
            broker_ca_bundle=broker_ca_bundle_path,
            cert_file=cert_file_path,
            private_key=private_key_path,
            brokers=[Broker.parse(url) for url in broker_urls_list],
        )

        # Set connectivity params
        config.connect_retries = 1
        config.reconnect_delay = 1
        config.reconnect_delay_max = 10

        # Create the DXL client
        dxl_client = DxlClient(config)
        # Connect to the fabric
        dxl_client.connect()

        self.mar_client = MarClient(dxl_client)

    @staticmethod
    def get_projection(collector, outputs):
        return {
            ProjectionConstants.NAME: collector,
            ProjectionConstants.OUTPUTS: outputs or MAR_COLLECTORS.get(collector),
        }

    def search(
        self,
        collector,
        outputs,
        filter_by=None,
        filter_operator=None,
        filter_value=None,
    ):
        """Active response search action.
        :param collector: collector name {string}
        :param outputs: which outputs to bring {string}
        :param filter_by: outputs to filter by {string}
        :param filter_operator: filter operator value {string}
        :param filter_value: value to filter by {string}
        :return: search result {dict}
        """
        if not filter_by and not filter_operator and not filter_value:
            result_context = self.mar_client.search(
                projections=[
                    {
                        ProjectionConstants.NAME: collector,
                        ProjectionConstants.OUTPUTS: outputs,
                    }
                ]
            )
        elif not filter_by or not filter_operator or not filter_value:
            msg = "ERROR: Filter-by, filter-operator & filter-value has to be inserted or none of them."
            raise Exception(
                msg
            )
        else:
            # Validate Operator.
            if FILTER_OPERATORS.get(filter_operator):
                filter_operator_value = FILTER_OPERATORS.get(filter_operator)
            else:
                msg = f"Error: No such operator - {filter_operator}"
                raise McAfeeActiveResponseError(
                    msg
                )

            # Run query, get result.
            result_context = self.mar_client.search(
                projections=[
                    {
                        ProjectionConstants.NAME: collector,
                        ProjectionConstants.OUTPUTS: outputs,
                    }
                ],
                conditions={
                    ConditionConstants.OR: [
                        {
                            ConditionConstants.AND: [
                                {
                                    ConditionConstants.COND_NAME: collector,
                                    ConditionConstants.COND_OUTPUT: filter_by,
                                    ConditionConstants.COND_OP: filter_operator_value,
                                    ConditionConstants.COND_VALUE: filter_value,
                                }
                            ]
                        }
                    ]
                },
            )
        if result_context.has_results:
            return result_context.get_results()
        return None

    def search_multiple_collectors(
        self,
        collectors,
        filter_collector=None,
        filter_by=None,
        filter_operator=None,
        filter_value=None,
    ):
        """Search by multiple collectors.
        :param collectors: list of collectors to search by {list}
        :param filter_collector: control filter  {string}
        :param filter_by: outputs to filter by {string}
        :param filter_operator: filter operator value {string}
        :param filter_value: value to filter by {string}
        :return:  {dict}
        """
        if not filter_collector:
            result_context = self.mar_client.search(
                projections=[self.get_projection(c, None) for c in collectors]
            )
        elif not filter_by or not filter_operator or not filter_value:
            msg = (
                "ERROR: Filter By, Filter Operator &"
                " Filter Value have to be inserted when you provide"
                " Filter Collector argument."
            )
            raise McAfeeActiveResponseError(
                msg
            )
        else:
            # Validate Operator.
            if FILTER_OPERATORS.get(filter_operator):
                filter_operator_value = FILTER_OPERATORS.get(filter_operator)
            else:
                msg = f"Error: No such operator - {filter_operator}"
                raise McAfeeActiveResponseError(
                    msg
                )
            result_context = self.mar_client.search(
                projections=[self.get_projection(c, None) for c in collectors],
                conditions={
                    ConditionConstants.OR: [
                        {
                            ConditionConstants.AND: [
                                {
                                    ConditionConstants.COND_NAME: filter_collector,
                                    ConditionConstants.COND_OUTPUT: filter_by,
                                    ConditionConstants.COND_OP: filter_operator_value,
                                    ConditionConstants.COND_VALUE: filter_value,
                                }
                            ]
                        }
                    ]
                },
            )
        if result_context.has_results:
            return result_context.get_results()
        return None


