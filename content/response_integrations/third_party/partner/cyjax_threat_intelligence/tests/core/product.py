from __future__ import annotations

import dataclasses
from typing import List, Optional

from TIPCommon.types import SingleJson


@dataclasses.dataclass(slots=True)
class CyjaxThreatIntelligence:
    ping_response: Optional[List[SingleJson]] = None
    domain_monitor_response: Optional[List[SingleJson]] = None
    enrich_iocs_response: Optional[SingleJson] = None
    list_data_breaches_response: Optional[List[SingleJson]] = None

    # Failure flags
    should_fail_ping: bool = False
    should_fail_domain_monitor: bool = False
    should_fail_enrich_iocs: bool = False
    should_fail_list_data_breaches: bool = False

    def get_ping(self) -> List[SingleJson]:
        if self.should_fail_ping:
            raise Exception("Failed to connect to CYJAX API")
        if self.ping_response is not None:
            return self.ping_response
        return [{"id": "ioc-1", "value": "1.1.1.1", "type": "ipv4"}]

    def get_domain_monitor(self) -> List[SingleJson]:
        if self.should_fail_domain_monitor:
            raise Exception("Failed to retrieve domain monitor data")
        if self.domain_monitor_response is not None:
            return self.domain_monitor_response
        return []

    def get_enrich_iocs(self) -> SingleJson:
        if self.should_fail_enrich_iocs:
            raise Exception("Failed to enrich IOCs")
        if self.enrich_iocs_response is not None:
            return self.enrich_iocs_response
        return {}

    def get_list_data_breaches(self) -> List[SingleJson]:
        if self.should_fail_list_data_breaches:
            raise Exception("Failed to retrieve data breaches")
        if self.list_data_breaches_response is not None:
            return self.list_data_breaches_response
        return []
