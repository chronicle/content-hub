from __future__ import annotations

import copy

import requests

headers = {
    "content-type": "application/json",
    "application_key": "application_key",
    "api_key": "api_key",
}

BASE_URL = "https://api.datadoghq.com"


class DataDogManager:
    """Datadog Manager"""

    def __init__(self, api_key, app_key):
        self.session = requests.Session()
        self.session.headers.update(headers)
        self.session.headers["DD-APPLICATION-KEY"] = app_key
        self.session.headers["DD-API-KEY"] = api_key

    def test_connectivity(self):
        url = f"{BASE_URL}/api/v1/validate"
        response = self.session.get(url)
        response.raise_for_status()
        try:
            response.json()
        except:
            raise Exception(response.content)

        return response.json()

    def get_logs(self, name_space, from_time, to_time):
        url = f"{BASE_URL}/api/v1/logs-queries/list"
        data = {
            "query": f"kube_namespace:{name_space}",
            "time": {
                "from": from_time,
                # "timezone": timezone,
                "to": to_time,
            },
        }
        response = self.session.post(url, json=data)
        response.raise_for_status()
        try:
            response.json()
        except:
            raise Exception(response.content)

        return response.json()

    def get_metrics_by_name(self, metric_name):
        url = f"{BASE_URL}/api/v1/metrics/{metric_name}"
        response = self.session.get(url)
        response.raise_for_status()
        try:
            response.json()
        except:
            raise Exception(response.content)

        return response.json()

    def get_processes_by_specific_tags(self, name_space, deployment=None):
        url = f"{BASE_URL}/api/v2/processes"
        if deployment is not None:
            params = {
                "tags": f"kube_namespace:{name_space},kube_deployment:{deployment}",
            }
        else:
            params = {"tags": f"kube_namespace:{name_space}"}
        response = self.session.get(url, params=params)
        response.raise_for_status()
        try:
            response.json()
        except:
            raise Exception(response.content)

        return response.json()

    def get_processes_by_tags(self, tags):
        url = f"{BASE_URL}/api/v2/processes"

        params = {"tags": tags}
        response = self.session.get(url, params=params)
        response.raise_for_status()
        try:
            response.json()
        except:
            raise Exception(response.content)

        return response.json()

    def get_a_monitor_by_id(self, monitor_id, type_of_alert, from_ts, to_ts):
        url = f"{BASE_URL}/api/v1/monitor/search"
        query = {"query": f"id:{monitor_id}"}
        response = self.session.get(url, params=query)
        response.raise_for_status()
        try:
            response.json()
        except:
            raise Exception(response.content)

        return response.json()

    def get_log_based_metrics(self, metric_id):
        url = f"{BASE_URL}/api/v2/logs/config/metrics/{metric_id}"
        response = self.session.get(url)
        response.raise_for_status()
        try:
            response.json()
        except:
            raise Exception(response.content)

        return response.json()

    def get_timeseries_point_metrics(self, query, from_unixtime, to_unixtime):
        url = "https://api.datadoghq.com/api/v1/query"
        query = {"query": query, "from": from_unixtime, "to": to_unixtime}
        response = self.session.get(url, params=query)
        response.raise_for_status()
        try:
            response.json()
        except:
            raise Exception(response.content)

        return response.json()

    def get_timeseries_point_metrics_cpu_pod(
        self,
        pod_name,
        from_unixtime,
        to_unixtime,
    ):
        url = "https://api.datadoghq.com/api/v1/query"
        query = {
            "query": f"avg:kubernetes.cpu.system.total{{pod_name:{pod_name}}}by{{pod_name,kube_namespace}}",
            "from": from_unixtime,
            "to": to_unixtime,
        }
        response = self.session.get(url, params=query)
        response.raise_for_status()
        try:
            response.json()
        except:
            raise Exception(response.content)

        return response.json()

    def get_timeseries_point_metrics_memory_pod(
        self,
        pod_name,
        from_unixtime,
        to_unixtime,
    ):
        url = "https://api.datadoghq.com/api/v1/query"
        query = {
            "query": f"avg:kubernetes.memory.usage_pct{{pod_name:{pod_name}}}by{{pod_name,kube_namespace}}",
            "from": from_unixtime,
            "to": to_unixtime,
        }
        response = self.session.get(url, params=query)
        response.raise_for_status()
        try:
            response.json()
        except:
            raise Exception(response.content)
        return response.json()

    def get_aws_rds_metrics_memory(
        self,
        db_instance_identifier,
        from_unixtime,
        to_unixtime,
    ):
        url = "https://api.datadoghq.com/api/v1/query"
        query = {
            "query": f"avg:aws.rds.freeable_memory{{dbinstanceidentifier:{db_instance_identifier}}}by{{dbinstanceidentifier}}",
            "from": from_unixtime,
            "to": to_unixtime,
        }
        response = self.session.get(url, params=query)
        response.raise_for_status()
        try:
            response.json()
        except:
            raise Exception(response.content)
        return response.json()

    def get_aws_rds_metrics_cpu(
        self,
        db_instance_identifier,
        from_unixtime,
        to_unixtime,
    ):
        url = "https://api.datadoghq.com/api/v1/query"
        query = {
            "query": f"avg:aws.rds.cpuutilization{{dbinstanceidentifier:{db_instance_identifier}}}by{{dbinstanceidentifier}}",
            "from": from_unixtime,
            "to": to_unixtime,
        }
        response = self.session.get(url, params=query)
        response.raise_for_status()
        try:
            response.json()
        except:
            raise Exception(response.content)
        return response.json()

    def get_aws_rds_metrics_storage(
        self,
        db_instance_identifier,
        from_unixtime,
        to_unixtime,
    ):
        url = "https://api.datadoghq.com/api/v1/query"
        query = {
            "query": f"avg:aws.rds.free_storage_space{{dbinstanceidentifier:{db_instance_identifier}}}by{{dbinstanceidentifier}}",
            "from": from_unixtime,
            "to": to_unixtime,
        }
        response = self.session.get(url, params=query)
        response.raise_for_status()
        try:
            response.json()
        except:
            raise Exception(response.content)
        return response.json()

    def get_active_metrics_list(self, from_unixtime, host):
        url = "https://api.datadoghq.com/api/v1/metrics"
        query = {"from": from_unixtime, "host": host}
        response = self.session.get(url, params=query)
        response.raise_for_status()
        try:
            response.json()
        except:
            raise Exception(response.content)

        return response.json()

    def get_all_hosts(self, filters, sort_direction, include_hosts_metadata=True):
        url = f"{BASE_URL}/api/v1/hosts"
        query = {
            "filter": filters,
            "sort_dir": sort_direction,
            "include_hosts_metadata": include_hosts_metadata,
        }

        response = self.session.get(url, params=query)
        response.raise_for_status()
        try:
            response.json()
        except:
            raise Exception(response.content)
        return response.json()

    def get_all_monitor_details(self, group_states, id_offset):
        url = f"{BASE_URL}/api/v1/monitor"

        query = {"group_states": group_states}
        response = self.session.get(url, params=query)
        response.raise_for_status()
        try:
            response.json()
        except:
            raise Exception(response.content)
        return response.json()

    def monitors_group_search(self, query="status:Alert", sort=None):
        url = f"{BASE_URL}/api/v1/monitor/groups/search"

        if sort is not None:
            query = {"query": query, "sort": sort}
        else:
            query = {"query": query}
        response = self.session.get(url, params=query)
        response.raise_for_status()
        try:
            response.json()
        except:
            raise Exception(response.content)
        return response.json()

    def search_monitors(self, query, sort_by="status,asc"):
        url = f"{BASE_URL}/api/v1/monitor/search"

        query = {"query": query, "sort": sort_by}
        response = self.session.get(url, params=query)
        response.raise_for_status()
        try:
            response.json()
        except:
            raise Exception(response.content)
        return response.json()

    def get_datadog_events(
        self,
        start_time,
        end_time,
        sources,
        tags="monitor",
        priority="all",
        unaggregated=True,
    ):
        url = f"{BASE_URL}/api/v1/events"
        query = {}
        data = {
            "start": start_time,
            "end": end_time,
            "sources": sources,
            "tags": tags,
            "priority": priority,
            "unaggregated": unaggregated,
        }
        for key, value in data.items():
            if value is not None:
                query[key] = value

        response = self.session.get(url, params=query)
        response.raise_for_status()
        try:
            response.json()
        except:
            raise Exception(response.content)
        return response.json()

    def get_event_details(self, event_id):
        url = f"{BASE_URL}/api/v1/events/{event_id}"

        response = self.session.get(url)
        response.raise_for_status()
        try:
            response.json()
        except:
            raise Exception(response.content)
        return response.json()

    def get_graph_snapshot(self, metric_query, start_time, end_time):
        url = "https://api.datadoghq.com/api/v1/graph/snapshot"
        query = {"metric_query": metric_query, "start": start_time, "end": end_time}
        response = self.session.get(url, params=query)
        response.raise_for_status()
        try:
            response.json()
        except:
            raise Exception(response.content)
        return response.json()


def get_unicode(telegram):
    return str(telegram)


def dict_to_flat(target_dict):
    """Receives nested dictionary and returns it as a flat dictionary.
    :param target_dict: {dict}
    :return: Flat dict : {dict}
    """
    target_dict = copy.deepcopy(target_dict)

    def expand(raw_key, raw_value):
        key = raw_key
        value = raw_value
        """
        :param key: {string}
        :param value: {string}
        :return: Recursive function.
        """
        if value is None:
            return [(get_unicode(key), "")]
        if isinstance(value, dict):
            # Handle dict type value
            return [
                (
                    f"{get_unicode(key)}_{get_unicode(sub_key)}",
                    get_unicode(sub_value),
                )
                for sub_key, sub_value in dict_to_flat(value).items()
            ]
        if isinstance(value, list):
            # Handle list type value
            count = 1
            l = []
            items_to_remove = []
            for value_item in value:
                if isinstance(value_item, dict):
                    # Handle nested dict in list
                    l.extend(
                        [
                            (
                                f"{get_unicode(key)}_{get_unicode(count)}_{get_unicode(sub_key)}",
                                sub_value,
                            )
                            for sub_key, sub_value in dict_to_flat(value_item).items()
                        ],
                    )
                    items_to_remove.append(value_item)
                    count += 1
                elif isinstance(value_item, list):
                    l.extend(
                        expand(get_unicode(key) + "_" + get_unicode(count), value_item),
                    )
                    count += 1
                    items_to_remove.append(value_item)

            for value_item in items_to_remove:
                value.remove(value_item)

            for value_item in value:
                l.extend([(get_unicode(key) + "_" + get_unicode(count), value_item)])
                count += 1

            return l
        return [(get_unicode(key), get_unicode(value))]

    items = [
        item
        for sub_key, sub_value in target_dict.items()
        for item in expand(sub_key, sub_value)
    ]
    return dict(items)
