import abc
import dataclasses
import copy

from TIPCommon.types import SingleJson

from sentinel_one_v2.core.datamodelsV2 import Alert
from sentinel_one_v2.tests.common import (
    generate_init_query_json,
    generate_final_response_json,
)


@dataclasses.dataclass(slots=True)
class SentinelOneV2(abc.ABC):
    simulate_api_error: bool = False
    agents: dict[str, SingleJson] = dataclasses.field(default_factory=dict)
    endpoint_responses: dict[str, dict[str, SingleJson]] = dataclasses.field(
        default_factory=dict
    )
    cloud_detection_alerts: dict[str, Alert] = dataclasses.field(default_factory=dict)
    threats: dict[str, SingleJson] = dataclasses.field(default_factory=dict)
    activities: list[SingleJson] = dataclasses.field(default_factory=list)
    _sites: dict[str, SingleJson] = dataclasses.field(default_factory=dict)
    _agents_by_site: dict[str, list[SingleJson]] = dataclasses.field(
        default_factory=dict
    )
    _query_status_call_count: int = 1
    simulate_transient_error: bool = False

    def add_agent(self, computer_name: str, raw_json_agent: SingleJson) -> None:
        """Add agent to the product"""
        self.agents[computer_name] = raw_json_agent
        agent_uuid: str = raw_json_agent["data"][0]["uuid"]
        self.endpoint_responses[agent_uuid] = _create_endpoint_response(agent_uuid)

    def add_cloud_detection_alert(
        self, alert_id: str, raw_json_alert: SingleJson
    ) -> None:
        """Add cloud detection alert to the product"""
        self.cloud_detection_alerts[alert_id] = Alert.from_json(
            copy.deepcopy(raw_json_alert)
        )

    def add_threat(self, threat_id: str, raw_json_threat: SingleJson) -> None:
        """Add threat to the product"""
        self.threats[threat_id] = raw_json_threat

    def add_activity(self, raw_json_activity: SingleJson) -> None:
        """Add activity to the product"""
        self.activities.append(raw_json_activity)

    def get_agent(self, computer_name) -> SingleJson:
        return self.agents[computer_name]

    def get_query_status_calls(self) -> int:
        return self._query_status_call_count

    def increment_query_status_calls(self) -> None:
        self._query_status_call_count += 1

    def get_init_response_by_uuid(self, uuid: str) -> SingleJson:
        return self.endpoint_responses[uuid]["initQuery"]

    def get_final_response_by_uuid(self, uuid: str) -> SingleJson:
        return self.endpoint_responses[uuid]["finalResponse"]

    def get_cloud_detection_alert(self, alert_id: str) -> Alert:
        return self.cloud_detection_alerts[alert_id]

    def add_site(self, site_response: SingleJson) -> None:
        """Adds mock sites from a raw API response."""
        for site in site_response.get("data", {}).get("sites", []):
            site_id = site.get("id")
            if site_id:
                self._sites[site_id] = site
                if site_id not in self._agents_by_site:
                    self._agents_by_site[site_id] = []

    def add_agent_to_site(self, agent_response: SingleJson) -> None:
        """Adds mock agents from a raw API response to their respective sites."""
        agent = agent_response.get("data", [])[0]
        site_id = agent.get("siteId")
        if site_id and site_id in self._sites:
            self._agents_by_site[site_id].append(agent)

    def get_site_by_name(self, site_name: str) -> SingleJson | None:
        """Finds a site by its name."""
        found_sites = [s for s in self._sites.values() if s.get("name") == site_name]
        if found_sites:
            return {"data": {"sites": found_sites}}
        return {"data": {"sites": []}}

    # pylint: disable=unused-argument
    def get_agents_by_site(
        self, site_ids: int, limit: int
    ) -> list[SingleJson]:
        """Retrieves all agents for a given site ID."""
        return {"data": self._agents_by_site.get(site_ids, [])}


def _create_endpoint_response(agent_uuid: str) -> dict[str, SingleJson]:
    init_query_json: SingleJson = generate_init_query_json(agent_uuid)
    final_response_json: SingleJson = generate_final_response_json(agent_uuid)
    return {
        "initQuery": init_query_json,
        "finalResponse": final_response_json,
    }
