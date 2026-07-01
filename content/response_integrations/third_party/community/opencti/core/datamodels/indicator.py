import re

import pycti
from core.datamodels.base_octi_object import BaseOCTIObject
from pydantic import AwareDatetime


class Indicator(BaseOCTIObject):
    """Represent the Indicator model."""
    name: str
    pattern: str
    description: str | None = None
    valid_from: AwareDatetime | None = None
    valid_until: AwareDatetime | None = None
    score: int | None = None
    labels: list[str] | None = None
    markings: list[str] | None = None
    
    def _compute_stix_id(self) -> str:
        """Build a deterministic STIX ID for this object.
        Returns:
            The generated STIX identifier.
        """
        return pycti.Indicator.generate_id(pattern=self.pattern)

    def _get_main_observable_type(self) -> str:
        """Infer the main observable type from the STIX pattern expression.
        Returns:
            The normalized OpenCTI observable type name.
        """
        match = re.search(r"\[\s*([a-z0-9-]+)\s*:", self.pattern.lower())
        if not match:
            raise ValueError("Unable to determine main observable type from Indicator pattern")
        stix_observable_type = match.group(1)
        mapping = {
            "artifact": "Artifact",
            "autonomous-system": "Autonomous-System",
            "directory": "Directory",
            "domain-name": "Domain-Name",
            "email-addr": "Email-Addr",
            "email-message": "Email-Message",
            "file": "StixFile",
            "hostname": "Hostname",
            "ipv4-addr": "IPv4-Addr",
            "ipv6-addr": "IPv6-Addr",
            "mac-addr": "Mac-Addr",
            "mutex": "Mutex",
            "network-traffic": "Network-Traffic",
            "process": "Process",
            "software": "Software",
            "url": "Url",
            "user-account": "User-Account",
            "windows-registry-key": "Windows-Registry-Key",
            "x509-certificate": "X509-Certificate",
        }
        if stix_observable_type not in mapping:
            raise ValueError(f"Unsupported observable type in Indicator pattern: {stix_observable_type}")
        return mapping[stix_observable_type]
    
    def to_input_variables(self) -> dict:
        """Serialize the model into OpenCTI GraphQL payload.
        Returns:
            A dictionary matching OpenCTI input variable names.
        """
        input_variables = {
            "stix_id": self._compute_stix_id(),
            "name": self.name,
            "pattern": self.pattern,
            "pattern_type": "stix",
            "description": self.description,
            "valid_from": self.valid_from.isoformat() if self.valid_from else None,
            "valid_until": self.valid_until.isoformat() if self.valid_until else None,
            "x_opencti_score": self.score,
            "x_opencti_main_observable_type": self._get_main_observable_type(),
            "objectLabel": self.labels,
            "objectMarking": self._compute_markings_ids(),
        }
        return self._keep_set_variables_only(input_variables)
