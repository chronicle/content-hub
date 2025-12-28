from __future__ import annotations

import base64
import re
import uuid

import requests

HTTP_ERRORS = {
    401: "Unauthorized - is set if the authentication failed for the request (e.g. the API key is incorrect or missing)",
    403: "Forbidden - is set if the request is not authorized to consume the desired functionality (e.g. the API is not enabled for the used API key)",
    405: "Method not allowed - The HTTP method is other than POST",
    429: "Too many requests - More than 10 requests per second have been issued from the same IP address",
}
REPORTS = {
    "Antiphishing Activity": 1,
    "Blocked Applications": 2,
    "Blocked Websites": 3,
    "Data Protection": 5,
    "Device Control Activity": 6,
    "Endpoint Modules Status": 7,
    "Endpoint Protection Status": 8,
    "Firewall Activity": 9,
    "Malware Status": 12,
    "Monthly License Usage": 13,
    "Network Status": 14,
    "On demand scanning": 15,
    "Policy Compliance": 16,
    "Security Audit": 17,
    "Security Server Status": 18,
    "Top 10 Detected Malware": 19,
    "Top 10 Infected Endpoints": 21,
    "Update Status": 22,
    "Upgrade Status": 23,
    "AWS Monthly Usage": 24,
    "Endpoint Encryption Status": 30,
    "HyperDetect Activity": 31,
    "Network Patch Status": 32,
    "Sandbox Analyzer Failed Submissions": 33,
    "Network Incidents": 34,
    "Email Security Usage": 29,
}

ACTION_STATUSES = {
    "None": 0,
    "Pending remove": 1,
    "Pending restore": 2,
    "Remove failed": 3,
    "Restore failed": 4,
    "Pending Save": 16,
    "Failed Save": 17,
}

# urls
COMPANIES_URL = "{}/v1.0/jsonrpc/companies"
LICENSING_URL = "{}/v1.0/jsonrpc/licensing"
ACCOUNTS_URL = "{}/v1.0/jsonrpc/accounts"
NETWORK_URL = "{}/v1.0/jsonrpc/network"
PACKAGES_URL = "{}/v1.0/jsonrpc/packages"
POLICIES_URL = "{}/v1.0/jsonrpc/policies"
INTEGRATIONS_URL = "{}/v1.0/jsonrpc/integrations"
REPORTS_URL = "{}/v1.0/jsonrpc/reports"
PUSH_URL = "{}/v1.0/jsonrpc/push"
INCIDENTS_URL = "{}/v1.0/jsonrpc/incidents"
QUARANTINE_URL = "{}/v1.0/jsonrpc/quarantine"
GENERAL_URL = "{}/v1.0/jsonrpc/general"
ERRORS = {}


# =====================================
#              CLASSES                #
# =====================================


class BitdefenderGravityZoneManagerError(Exception):
    """General Exception for microsoft graph security manager"""


class BitdefenderGravityZoneManager:
    def __init__(self, api_key: str, verify_ssl: bool = False):
        self.authorization = base64.b64encode((api_key + ":").encode("UTF-8")).decode(
            "UTF-8",
        )
        self.session = requests.Session()
        self.session.verify = verify_ssl
        self.session.headers.update(
            {
                "Content-Type": "application/json",
                "Authorization": f"Basic {self.authorization}",
            },
        )

    def validate_response(self, response, error_msg="An error occurred"):
        status_code = -1
        if isinstance(response, int):
            status_code = response
        else:
            status_code = response.status_code

        if status_code != 200:
            if status_code == -1:
                raise BitdefenderGravityZoneManagerError(
                    f"{status_code}: {'Unable to validate status code of request'} {response}",
                )
            raise BitdefenderGravityZoneManagerError(
                f"{response.status_code}: {HTTP_ERRORS.get(response.status_code)} {response}",
            )

    def apikey_details(self, access_url):
        """Retrieve details of the current API key
        :return: dict of key details
        """
        method = "getApiKeyDetails"
        params = {}
        res = self.control_center_put(GENERAL_URL.format(access_url), method, params)[0]

        return {"result": res.get("result", {})}

    def get_endpoints_list(
        self,
        access_url,
        parent_id,
        endpoints,
        filter_best,
        filter_exchange,
        filter_relays,
        filter_security_servers,
        filter_depth_allrecursive,
        filter_ssid,
        filter_macaddrs,
        filter_name,
    ):
        """Retrieve a list of all endpoints with given filters.
        :return: {list} of endpoints {dicts}
        """
        method = "getEndpointsList"
        params = {}
        if parent_id:
            params["parentId"] = parent_id
        if endpoints == "Managed":
            params["isManaged"] = True
        elif endpoints == "Unmanaged":
            params["isManaged"] = False
        params["filters"] = {}
        params["filters"]["security"] = {}
        params["filters"]["security"]["management"] = {
            "managedWithBest": filter_best,
            "managedExchangeServers": filter_exchange,
            "managedRelays": filter_relays,
            "securityServers": filter_security_servers,
        }
        params["filters"]["depth"] = {"allItemsRecursively": filter_depth_allrecursive}
        if filter_ssid:
            if "details" not in params["filters"]:
                params["filters"]["details"] = {}
            params["filters"]["details"]["ssid"] = filter_ssid
        if filter_macaddrs:
            if "details" not in params["filters"]:
                params["filters"]["details"] = {}
            params["filters"]["details"]["macs"] = filter_macaddrs
        if filter_name:
            if "details" not in params["filters"]:
                params["filters"]["details"] = {}
            if len(filter_name) > 0 and len(filter_name) < 3:
                raise BitdefenderGravityZoneManagerError(
                    "{}: {} {}".format(
                        "get_endpoints_list",
                        "Minimum length required for 'name' filter is 3 characters.",
                        params,
                    ),
                )
            if len(filter_name) > 2:
                params["filters"]["details"]["name"] = filter_name
        print(f"Making request: \n{params}")
        res = self.control_center_paged(NETWORK_URL.format(access_url), method, params)

        return res

    def blocklist_hashes_list(self, access_url):
        """Retrieve the hash blocklist.
        :return: {list} of blocklist objects {dicts}
        """
        method = "getBlocklistItems"
        params = {}
        res = self.control_center_paged(
            INCIDENTS_URL.format(access_url),
            method,
            params,
        )

        return res

    def blocklist_hashes_remove(self, access_url, hash_id):
        """Remove a hash from the blocklist by given hash ID.
        :return: {bool} true == success
        """
        method = "removeFromBlocklist"
        params = {"hashItemId": hash_id}
        res = self.control_center_put(INCIDENTS_URL.format(access_url), method, params)[
            0
        ]

        return {"result": res.get("result", False)}

    def get_managed_endpoint(self, access_url, endpoint_id):
        """Retrieve managed endpoint details by ID
        :return: {dict} of managed endpoint details.
        """
        method = "getManagedEndpointDetails"
        params = {"endpointId": endpoint_id}

        res = self.control_center_put(NETWORK_URL.format(access_url), method, params)[0]

        return {"result": res.get("result", {})}

    def isolate_endpoint(self, access_url, endpoint_id):
        """Isolate an endpoint
        :return: {bool} true == success
        """
        method = "createIsolateEndpointTask"
        params = {"endpointId": endpoint_id}

        res = self.control_center_put(INCIDENTS_URL.format(access_url), method, params)[
            0
        ]

        return {"result": res.get("result", False)}

    def isolate_endpoint_restore(self, access_url, endpoint_id):
        """Restore an isolated endpoint
        :return: {bool} true == success
        """
        method = "createRestoreEndpointFromIsolationTask"
        params = {"endpointId": endpoint_id}

        res = self.control_center_put(INCIDENTS_URL.format(access_url), method, params)[
            0
        ]

        return {"result": res.get("result", False)}

    def blocklist_hashes_add(self, access_url, hash_csv, source_info):
        """Add a set of hashes to the blocklist. Separates sha256 and md5 into
            two different lists, as they require separate insertion.
        :return: {dict} of three lists, containing each hash and the relevant category.
        """
        method = "addToBlocklist"
        hash_list = hash_csv.split(",")
        hashes_sha256 = []
        hashes_md5 = []
        hashes_unknown = []

        for file_hash in hash_list:
            if self.is_md5(file_hash):
                hashes_md5.append(file_hash)
            elif self.is_sha256:
                hashes_sha256.append(file_hash)
            else:
                hashes_unknown.append(file_hash)

        if hashes_sha256:
            params = {
                "hashType": 1,
                "hashList": hashes_sha256,
                "sourceInfo": source_info,
            }
            res = self.control_center_put(
                INCIDENTS_URL.format(access_url),
                method,
                params,
            )[0]

        if hashes_md5:
            params = {"hashType": 2, "hashList": hashes_md5, "sourceInfo": source_info}
            res = self.control_center_put(
                INCIDENTS_URL.format(access_url),
                method,
                params,
            )[0]

        if hashes_unknown:
            raise BitdefenderGravityZoneManagerError(
                f"{'blocklist_hashes_add'}: {'Unsupported hashes were found and not submitted. At this time, Bitdefender only accepts SHA256 or MD5.'} {hashes_unknown}",
            )

        return {
            "result": {
                "hashes_sha256": hashes_sha256,
                "hashes_md5": hashes_md5,
                "hashes_failed": hashes_unknown,
            },
        }

    def task_create_scan(
        self,
        access_url,
        target_ids,
        scan_type,
        task_name,
        scan_depth,
        scan_paths,
    ):
        """Create a scan task
        :return: {bool} true == success
        """
        method = "createScanTask"
        target_id_list = target_ids.split(",")
        scan_type_int = 1
        if scan_type == "Full":
            scan_type_int = 2
        elif scan_type == "Memory":
            scan_type_int = 3
        elif scan_type == "Custom":
            scan_type_int = 4
        scan_depth_int = 2
        if scan_type == "Aggressive":
            scan_depth_int = 1
        elif scan_type == "Permissive":
            scan_depth_int = 3
        scan_path_list = scan_paths.split(",")

        params = {
            "targetIds": target_id_list,
            "type": scan_type_int,
            "name": task_name,
            "customScanSettings": {
                "scanDepth": scan_depth_int,
                "scanPath": scan_path_list,
            },
        }
        res = self.control_center_put(NETWORK_URL.format(access_url), method, params)[0]

        return {"result": res.get("result", False)}

    def task_create_scan_macaddr(
        self,
        access_url,
        target_macaddrs,
        scan_type,
        task_name,
        scan_depth,
        scan_paths,
    ):
        """Create a scan task
        :return: {bool} true == success
        """
        method = "createScanTaskByMac"
        target_macaddrs_list = target_macaddrs.split(",")
        if len(target_macaddrs_list > 100):
            raise BitdefenderGravityZoneManagerError(
                f"{'task_create_scan_macaddr'}: {'Too many MAC addresses were given. Max 100.'} {target_macaddrs_list}",
            )
        scan_type_int = 1
        if scan_type == "Full":
            scan_type_int = 2
        elif scan_type == "Memory":
            scan_type_int = 3
        elif scan_type == "Custom":
            scan_type_int = 4
        scan_depth_int = 2
        if scan_type == "Aggressive":
            scan_depth_int = 1
        elif scan_type == "Permissive":
            scan_depth_int = 3
        scan_path_list = scan_paths.split(",")

        params = {
            "macAddresses": target_macaddrs_list,
            "type": scan_type_int,
            "name": task_name,
            "customScanSettings": {
                "scanDepth": scan_depth_int,
                "scanPath": scan_path_list,
            },
        }
        res = self.control_center_put(NETWORK_URL.format(access_url), method, params)[0]

        return {"result": res.get("result", False)}

    def task_scan_list(self, access_url, task_name, task_status):
        """Retrieve the scan tasks list.
        :return: {list} of scan tasks {dicts}
        """
        method = "getScanTasksList"
        params = {}
        params["name"] = task_name
        if task_status == "Pending":
            params["staus"] = 1
        elif task_status == "In-progress":
            params["staus"] = 2
        elif task_status == "Finished":
            params["staus"] = 3

        res = self.control_center_paged(NETWORK_URL.format(access_url), method, params)

        return res

    def groups_custom_list(self, access_url, parent_id):
        """Retrieve custom lists, associated with a given parent_id (if provided)
        :return: {list} of custom lists and their info {dicts}
        """
        method = "getCustomGroupsList"
        params = {"parentId": parent_id}

        res = self.control_center_put(NETWORK_URL.format(access_url), method, params)
        json_data = res[0]
        satus_code = res[1]
        self.validate_response(satus_code)

        return {"items": json_data.get("result", [])}

    def label_endpoint_set(self, access_url, endpoint_id, label):
        """Add a label to an endpoint
        :return: {bool} true == success
        """
        method = "setEndpointLabel"
        params = {"endpointId": endpoint_id, "label": label}

        res = self.control_center_put(NETWORK_URL.format(access_url), method, params)[0]

        return {"result": res.json().get("result", False)}

    def control_center_put(self, url, method, params):
        """Actions 'single use' requests that typically return only a boolean response or single list/dict
        :return: {dict},{int} A tuple, containing a json response dict followed by an http status code
        """
        json = {
            "method": method,
            "params": params,
            "jsonrpc": "2.0",
            "id": str(uuid.uuid4()),
        }
        res = self.session.post(url, json=json)
        self.validate_response(res)
        json_data = res.json()

        if "error" in json_data:
            raise BitdefenderGravityZoneManagerError(
                f"{json_data['error']['message']}: {json_data['error']['code']} {json_data['error']['data']}",
            )

        return json_data, res.status_code

    def control_center_paged(self, request_url, method, params):
        """Handles larger requests that require pagination.
        :return: {list} Typically contains a list of {dicts} depending on the request made.
        """
        total_items = []
        params["page"] = 1

        json = {
            "method": method,
            "params": params,
            "jsonrpc": "2.0",
            "id": str(uuid.uuid4()),
        }

        # Make initial request
        res = self.session.post(request_url, json=json)
        self.validate_response(res)

        json_data = res.json()

        if "error" in json_data:
            raise BitdefenderGravityZoneManagerError(
                f"{json_data['error']['message']}: {json_data['error']['code']} {json_data['error']['data']}",
            )

        page_count = json_data["result"]["pagesCount"]
        per_page = json_data["result"]["perPage"]
        items = json_data["result"]["items"]

        for item in items:
            total_items.append(item)

        if page_count > 1:
            for current_page in range(2, page_count):
                # Make any additional paginated requests
                params["page"] = current_page
                res = self.session.post(request_url, json=json)
                self.validate_response(res)

                json_data = res.json()

                items = json_data["result"]["items"]

                for item in items:
                    total_items.append(item)

        return {"items": total_items}

    def network_inventory_list(
        self,
        access_url,
        parent_id,
        filter_groups,
        filter_ec2,
        filter_computers,
        filter_vms,
        filter_best,
        filter_exchange,
        filter_relays,
        filter_security_servers,
        filter_depth_allrecursive,
        filter_ssid,
        filter_macaddrs,
        filter_name,
    ):
        """Retrieves network inventory list.
        :return: {list} of network inventory {dicts}
        """
        method = "getNetworkInventoryItems"
        params = {"parentId": parent_id}
        macaddrs_list = []
        macaddrs_list = filter_macaddrs.split(",")
        params["filters"] = {}
        params["filters"]["type"] = {
            "groups": filter_groups,
            "ec2Instances": filter_ec2,
            "computers": filter_computers,
            "virtualMachines": filter_vms,
        }
        params["filters"]["security"] = {}
        params["filters"]["security"]["management"] = {
            "managedWithBest": filter_best,
            "managedExchangeServers": filter_exchange,
            "managedRelays": filter_relays,
            "securityServers": filter_security_servers,
        }
        params["filters"]["depth"] = {"allItemsRecursively": filter_depth_allrecursive}
        params["filters"]["details"] = {"ssid": filter_ssid, "macs": macaddrs_list}
        if len(filter_name) > 0 and len(filter_name) < 3:
            raise BitdefenderGravityZoneManagerError(
                "{}: {} {}".format(
                    "network_inventory_list",
                    "Minimum length required for 'name' filter is 3 characters.",
                    params,
                ),
            )
        if len(filter_name) > 2:
            params["filters"]["details"]["name"] = filter_name
        res = self.control_center_paged(NETWORK_URL.format(access_url), method, params)

        return res

    def quarantine_item_list(
        self,
        access_url,
        endpoint_id,
        service,
        filter_threat_name,
        filter_start_date,
        filter_end_date,
        filter_file_path,
        filter_ip_addr,
        filter_action_status,
    ):
        """Retrieve the list of quarantined items
        :return: {list} of quarantined item {dicts}
        """
        method = "getQuarantineItemsList"
        params = {"endpointId": endpoint_id}
        params["filters"] = {}
        if filter_threat_name:
            params["filters"]["threatName"] = filter_threat_name
        if filter_start_date:
            params["filters"]["startDate"] = filter_start_date
        if filter_end_date:
            params["filters"]["endDate"] = filter_end_date
        if filter_file_path:
            params["filters"]["filePath"] = filter_file_path
        if filter_ip_addr:
            params["filters"]["ip"] = filter_ip_addr
        params["filters"]["actionStatus"] = ACTION_STATUSES.get(filter_action_status)

        res = self.control_center_paged(
            QUARANTINE_URL.format(access_url) + "/" + service.lower(),
            method,
            params,
        )

        return res

    def policy_list(self, access_url):
        """Retrieve the list of policies
        :return: {list} of policy {dicts}
        """
        method = "getPoliciesList"
        params = {}

        res = self.control_center_paged(POLICIES_URL.format(access_url), method, params)

        return res

    def policy_details(self, access_url, policy_id):
        """Retrieve the details for a given policy ID
        :return: {list} of policy detail {dicts}
        """
        method = "getPolicyDetails"
        params = {"policyId": policy_id}

        res = self.control_center_put(POLICIES_URL.format(access_url), method, params)[
            0
        ]

        return {"result": res.get("result", [])}

    def integration_aws_ec2_usage(self, access_url, target_month):
        """This method exposes the hourly usage for each Amazon instance category (micro, medium etc.).
        :return: {dict} of results
        """
        method = "getHourlyUsageForAmazonEC2Instances"
        params = {"targetMonth": target_month}

        res = self.control_center_put(
            INTEGRATIONS_URL.format(access_url),
            method,
            params,
        )[0]

        return {"result": res.get("result", {})}

    def quarantine_item_remove(self, access_url, quarantine_item_ids, service):
        """Removes an item from quarantine.
        :return: {bool} true == success
        """
        method = "createRemoveQuarantineItemTask"
        quarantine_item_ids_list = quarantine_item_ids.split(",")
        params = {"quarantineItemsIds": quarantine_item_ids_list}

        res = self.control_center_put(
            QUARANTINE_URL.format(access_url) + "/" + service.lower(),
            method,
            params,
        )[0]

        return {"result": res.get("result", False)}

    def quarantine_item_restore(
        self,
        access_url,
        quarantine_item_ids,
        service,
        add_exclusion,
        restore_location,
    ):
        """Restores an item in the quarantine back to it's original location, or specified restore location.
        :return: {bool} true == success
        """
        method = "createRestoreQuarantineItemTask"
        quarantine_item_ids_list = quarantine_item_ids.split(",")
        params = {
            "quarantineItemsIds": quarantine_item_ids_list,
            "locationToRestore": restore_location,
            "addExclusionInPolicy": add_exclusion,
        }

        res = self.control_center_put(
            QUARANTINE_URL.format(access_url) + "/" + service.lower(),
            method,
            params,
        )[0]

        return {"result": res.get("result", False)}

    def quarantine_item_exchange_restore(
        self,
        access_url,
        quarantine_item_ids,
        username,
        password,
        email,
        ews_url,
    ):
        """Restore a quarantined exchange item
        :return: {bool} true == success
        """
        method = "createRestoreQuarantineExchangeItemTask"
        quarantine_item_ids_list = quarantine_item_ids.split(",")
        params = {
            "quarantineItemsIds": quarantine_item_ids_list,
            "username": username,
            "password": password,
        }
        if email:
            params["email"] = email
        if ews_url:
            params["ewsUrl"] = ews_url

        res = self.control_center_put(
            QUARANTINE_URL.format(access_url) + "/exchange",
            method,
            params,
        )[0]

        return {"result": res.get("result", False)}

    def quarantine_item_add(self, access_url, endpoint_ids, file_path):
        """Add a file to the quarantine based on file path
        :return: {bool} true == success
        """
        method = "createAddFileToQuarantineTask"
        endpoint_ids_list = endpoint_ids.split(",")
        params = {"endpointIds": endpoint_ids_list, "filePath": file_path}

        res = self.control_center_put(
            QUARANTINE_URL.format(access_url),
            method,
            params,
        )[0]

        return {"result": res.get("result", False)}

    def report_list(self, access_url, report_name, report_type):
        """Retrieve the list of reports
        :return: {list} of reports {dicts}
        """
        method = "getReportsList"
        params = {}
        if report_name:
            params["name"] = report_name
        if report_type:
            params["type"] = REPORTS.get(report_type)

        res = self.control_center_paged(REPORTS_URL.format(access_url), method, params)

        return res

    def report_getlinks(self, access_url, report_id):
        """Retrieve the download links for a given report
        :return: {dict} of results
        """
        method = "getDownloadLinks"
        params = {"reportId": report_id}

        res = self.control_center_put(REPORTS_URL.format(access_url), method, params)[0]

        return {"result": res.get("result", {})}

    def is_md5(self, hash_string):
        return re.match(r"(^[a-fA-F\d]{32}$)", hash_string)

    def is_sha256(self, hash_string):
        return re.match(r"(^[A-Fa-f0-9]{64}$)", hash_string)
