from __future__ import annotations
from .datamodels import *


class IvantiEndpointManagerParser:

    def build_query_objects(self, raw_data):
        queries = (
            raw_data.get("QueryList", {}).get("Queries", {}).get("Query", [])
            if raw_data.get("QueryList", {}).get("Queries", {})
            else []
        )
        items = queries if isinstance(queries, list) else [queries]
        return [self.build_query_object(item) for item in items]

    @staticmethod
    def build_query_object(raw_data):
        return Query(raw_data=raw_data, name=raw_data.get("QueryName"))

    def build_delivery_method_objects(self, raw_data):
        delivery_methods = (
            raw_data.get("DeliveryMethodList", {})
            .get("DeliveryMethods", {})
            .get("SwdDeliveryMethod", [])
            if raw_data.get("DeliveryMethodList", {}).get("DeliveryMethods", {})
            else []
        )
        items = (
            delivery_methods
            if isinstance(delivery_methods, list)
            else [delivery_methods]
        )
        return [self.build_delivery_method_object(item) for item in items]

    @staticmethod
    def build_delivery_method_object(raw_data):
        return DeliveryMethod(
            raw_data=raw_data,
            name=raw_data.get("DeliveryName"),
            type=raw_data.get("DeliveryType"),
            description=raw_data.get("DeliveryDescription"),
        )

    def build_field_objects(self, raw_data):
        columns = raw_data.get("ColumnSetColumnList", {}).get("Columns", {})
        fields = columns.get("string", []) if columns else []
        items = fields if isinstance(fields, list) else [fields]
        return [self.build_field_object(item) for item in items]

    @staticmethod
    def build_field_object(raw_data):
        return Field(raw_data=raw_data, name=raw_data)

    def build_machine_objects(self, raw_data):
        devices = raw_data.get("DeviceList", {}).get("Devices", {})
        machines = devices.get("Device", []) if devices else []
        items = machines if isinstance(machines, list) else [machines]
        return [self.build_machine_object(item) for item in items]

    @staticmethod
    def build_machine_object(raw_data):
        return Machine(
            raw_data=raw_data,
            guid=raw_data.get("GUID"),
            device_name=raw_data.get("DeviceName"),
            domain_name=raw_data.get("DomainName"),
            last_login=raw_data.get("LastLogin"),
            ip_address=raw_data.get("IPAddress"),
            subnet_mask=raw_data.get("SubNetMask"),
            mac_address=raw_data.get("MACAddress"),
            os_name=raw_data.get("OSName"),
        )

    @staticmethod
    def parse_machine_details(raw_data):
        value_pairs = (
            raw_data.get("DeviceDataList", {})
            .get("MachineData", {})
            .get("ValuePair", [])
        )
        items = value_pairs if isinstance(value_pairs, list) else [value_pairs]
        columns_dict = {}
        for item in items:
            if item.get("Value"):
                columns_dict[
                    item.get("Column")
                    .replace('"', "")
                    .replace(" ", "")
                    .replace(".", "_")
                ] = item.get("Value")

        return columns_dict

    def build_vulnerability_objects(self, raw_data):
        vulnerabilities = (
            raw_data.get("VulnerabilityList", {})
            .get("Vulnerability", {})
            .get("Vulnerability", [])
            if raw_data.get("VulnerabilityList", {}).get("Vulnerability", {})
            else []
        )
        items = (
            vulnerabilities if isinstance(vulnerabilities, list) else [vulnerabilities]
        )
        return [self.build_vulnerability_object(item) for item in items]

    @staticmethod
    def build_vulnerability_object(raw_data):
        return Vulnerability(
            raw_data=raw_data, severity_code=raw_data.get("SeverityCode")
        )

    def build_package_objects(self, raw_data):
        packages = (
            raw_data.get("DistributionPackageList", {})
            .get("DistributionPackages", {})
            .get("DistributionPackage", [])
            if raw_data.get("DistributionPackageList", {}).get(
                "DistributionPackages", {}
            )
            else []
        )
        items = packages if isinstance(packages, list) else [packages]
        return [self.build_package_object(item) for item in items]

    @staticmethod
    def build_package_object(raw_data):
        return Package(
            raw_data=raw_data,
            type=raw_data.get("PackageType"),
            name=raw_data.get("PackageName"),
            description=raw_data.get("PackageDescription"),
            primary_file=raw_data.get("PackagePrimaryFile"),
        )

    def build_column_set_objects(self, raw_data):
        column_sets = (
            raw_data.get("ColumnSetList", {}).get("ColumnSets", {}).get("ColumnSet", [])
            if raw_data.get("ColumnSetList", {}).get("ColumnSets", {})
            else []
        )
        items = column_sets if isinstance(column_sets, list) else [column_sets]
        return [self.build_column_set_object(item) for item in items]

    @staticmethod
    def build_column_set_object(raw_data):
        return ColumnSet(raw_data=raw_data, name=raw_data.get("Name"))

    def build_query_result_objects(self, raw_data):
        results = (
            raw_data.get("DataSet", {})
            .get("diffgr:diffgram", {})
            .get("NewDataSet", {})
            .get("Table", [])
        )
        items = results if isinstance(results, list) else [results]
        return [self.build_query_result_object(item) for item in items]

    @staticmethod
    def build_query_result_object(raw_data):
        return QueryResult(
            raw_data=raw_data,
            device_name=raw_data.get("Device_x0020_Name"),
            type=raw_data.get("Type"),
            os_name=raw_data.get("OS_x0020_Name"),
        )

    def build_task_result_object(self, raw_data):
        device_data = raw_data.get("TaskMachineDataList", {}).get("DeviceData", {})
        machines = device_data.get("TaskMachineData", []) if device_data else []
        items = machines if isinstance(machines, list) else [machines]
        return TaskResult(
            raw_data=raw_data,
            machine_data=[self.build_task_machine_object(item) for item in items],
        )

    @staticmethod
    def build_task_machine_object(raw_data):
        return TaskMachine(
            raw_data=raw_data,
            guid=raw_data.get("GUID"),
            name=raw_data.get("Name"),
            status=raw_data.get("Status"),
        )
