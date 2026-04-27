from __future__ import annotations
class ExternalReference:
    MITRE_ATTACK = "mitre-attack"

    def __init__(self, raw_data, external_id, url, source_name):
        self.raw_data = raw_data
        self.external_id = external_id
        self.url = url
        self.source_name = source_name


class Attack:
    def __init__(
        self,
        raw_data,
        attack_id,
        name,
        attack_type,
        external_references,
        description,
        detection,
        x_mitre_platforms,
        created_by_ref,
        x_mitre_deprecated,
        labels,
        mitre_external_reference,
    ):
        self.raw_data = raw_data
        self.attack_id = attack_id
        self.attack_type = attack_type
        self.name = name
        self.external_references = external_references
        self.description = description
        self.detection = detection
        self.x_mitre_platforms = [] if x_mitre_platforms is None else x_mitre_platforms
        self.mitre_external_reference = mitre_external_reference
        self.url = (
            self.mitre_external_reference.url if self.mitre_external_reference else None
        )
        self.mitre_external_id = (
            self.mitre_external_reference.external_id
            if self.mitre_external_reference
            else None
        )
        self.created_by_ref = created_by_ref
        self.x_mitre_deprecated = x_mitre_deprecated
        self.labels = [] if labels is None else labels

    def to_json(self):
        return self.raw_data

    def to_data_table(self):
        return {
            "Name": self.name,
            "Description": self.description,
            "Detection": self.detection,
            "OS": " ".join(self.x_mitre_platforms),
        }

    def to_mitigations_data_table(self):
        return {
            "Name": self.name,
            "Description": self.description,
            "Deprecated": self.x_mitre_deprecated,
        }

    def to_intrusion_data_table(self):
        return {
            "Name": self.name,
            "Description": self.description,
            "Affected Platforms": " ".join(self.x_mitre_platforms),
            "Type": self.attack_type,
            "Label": " ".join(self.labels),
            "External ID": self.mitre_external_id,
        }

    def contains_external_id(self, external_id):
        if self.external_references is None:
            return False

        for external_ref in self.external_references:
            if external_id == external_ref.get("external_id"):
                return True

        return False


class AttackRelationship(Attack):
    def __init__(
        self,
        raw_data,
        attack_id,
        name,
        attack_type,
        relationship_type,
        target_ref,
        source_ref,
        external_references,
        description,
        detection,
        x_mitre_platforms,
        created_by_ref,
        x_mitre_deprecated,
        labels,
        mitre_external_reference,
    ):
        super(AttackRelationship, self).__init__(
            raw_data,
            attack_id,
            name,
            attack_type,
            external_references,
            description,
            detection,
            x_mitre_platforms,
            created_by_ref,
            x_mitre_deprecated,
            labels,
            mitre_external_reference,
        )
        self.relationship_type = relationship_type
        self.target_ref = target_ref
        self.source_ref = source_ref

    def to_json(self):
        return self.raw_data

    def type_is(self, relationship_type):
        return self.relationship_type == relationship_type

    def ref_equal(self, ref, ref_type):
        return getattr(self, ref_type) == ref
