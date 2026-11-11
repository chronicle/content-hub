import abc
from typing import MutableMapping, List
from proof_point_tap.core.datamodels import (
    Campaign,
    Event,
    ThreatForensic,
)


class ProofPointTAP(abc.ABC):

    def __init__(self) -> None:
        self._campaigns: MutableMapping[str, Campaign] = {}
        self._events: MutableMapping[str, Event] = {}
        self._threat_forensics: MutableMapping[str, List[ThreatForensic]] = {}

    def add_campaign(self, campaign: Campaign) -> None:
        self._campaigns = campaign

    def get_campaign(self) -> Campaign:
        return self._campaigns

    def add_threat_forensics(self, threat_forensics: ThreatForensic) -> None:
        self._threat_forensics = threat_forensics

    def get_threat_forensics(self) -> ThreatForensic:
        return self._threat_forensics

    def add_event(self, event: Event) -> None:
        self._events = event

    def get_events(self) -> Event:
        return self._events
