from __future__ import annotations

from typing import Literal

from core.datamodels.base_octi_object import BaseOCTIObject
from core.utils import get_hash_type


class Observable(BaseOCTIObject):
    """Represent the Observable model."""

    type: Literal[
        "Domain-Name",
        "Url",
        "Hostname",
        "Email-Message",
        "Email-Addr",
        "IPv4-Addr",
        "IPv6-Addr",
        "StixFile",
        "File-Name",
    ]
    value: str
    description: str | None = None
    labels: list[str] | None = None
    markings: list[str] | None = None
    score: int | None = None
    create_indicator: bool = False

    def _compute_stix_id(self) -> None:
        # OpenCTI computes deterministic IDs for observables from observableData.
        # We do not build a deterministic ID client-side for this entity.
        """No deterministic STIX ID is generated client-side for observables."""
        pass

    def _build_observable_data(self) -> dict:
        """Build the observableData payload expected by OpenCTI.
        Returns:
            A dictionary containing the type-specific observable payload.
        """
        if self.type == "Email-Message":
            observable_data = {"type": "email-message", "subject": self.value}
        elif self.type == "StixFile":
            hash_type = get_hash_type(self.value)
            match hash_type:
                case "md5":
                    hashes = {"md5": self.value}
                case "sha1":
                    hashes = {"sha-1": self.value}
                case "sha256":
                    hashes = {"sha-256": self.value}
                case "sha512":
                    hashes = {"sha-512": self.value}
                case _:
                    raise ValueError("Observable Value is not a supported hash type")
            observable_data = {"type": "file", "hashes": hashes}
        elif self.type == "File-Name":
            observable_data = {"type": "file", "name": self.value}
        else:
            observable_data = {"type": self.type, "value": self.value}
        if self.description:
            observable_data["x_opencti_description"] = self.description
        return observable_data

    def to_input_variables(self) -> dict:
        """Serialize the model into OpenCTI GraphQL payload.
        Returns:
            A dictionary matching OpenCTI input variable names.
        """
        input_variables = {
            "observableData": self._build_observable_data(),
            "objectMarking": self._compute_markings_ids(),
            "x_opencti_score": self.score,
            "createIndicator": self.create_indicator,
            "objectLabel": self.labels,
        }
        return self._keep_set_variables_only(input_variables)
