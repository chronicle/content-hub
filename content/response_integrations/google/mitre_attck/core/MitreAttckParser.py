from __future__ import annotations
from .datamodels import Attack, AttackRelationship, ExternalReference

OBJECT_KEY = "objects"
RELATIONSHIP_TYPE = "relationship"


class MitreAttckParser:
    @staticmethod
    def build_siemplify_attack_obj(attack_data):
        return Attack(
            raw_data=attack_data,
            attack_id=attack_data.get("id"),
            name=attack_data.get("name"),
            attack_type=attack_data.get("type"),
            external_references=attack_data.get("external_references"),
            description=attack_data.get("description"),
            detection=attack_data.get("x_mitre_detection"),
            x_mitre_platforms=attack_data.get("x_mitre_platforms"),
            created_by_ref=attack_data.get("created_by_ref"),
            x_mitre_deprecated=attack_data.get("x_mitre_deprecated"),
            labels=attack_data.get("labels"),
            mitre_external_reference=MitreAttckParser.get_mitre_external_reference(
                attack_data.get("external_references", {})
            ),
        )

    @staticmethod
    def build_siemplify_attack_relationship_obj(attack_data):
        return AttackRelationship(
            raw_data=attack_data,
            attack_id=attack_data.get("id"),
            name=attack_data.get("name"),
            attack_type=attack_data.get("type"),
            relationship_type=attack_data.get("relationship_type"),
            target_ref=attack_data.get("target_ref"),
            source_ref=attack_data.get("source_ref"),
            external_references=attack_data.get("external_references"),
            description=attack_data.get("description"),
            detection=attack_data.get("x_mitre_detection"),
            x_mitre_platforms=attack_data.get("x_mitre_platforms"),
            created_by_ref=attack_data.get("created_by_ref"),
            x_mitre_deprecated=attack_data.get("x_mitre_deprecated"),
            labels=attack_data.get("labels"),
            mitre_external_reference=MitreAttckParser.get_mitre_external_reference(
                attack_data.get("external_references", {})
            ),
        )

    @staticmethod
    def get_mitre_external_reference(external_references):
        for external_ref in external_references:
            if external_ref.get("source_name") == ExternalReference.MITRE_ATTACK:
                return ExternalReference(
                    raw_data=external_ref,
                    external_id=external_ref.get("external_id"),
                    url=external_ref.get("url"),
                    source_name=external_ref.get("source_name"),
                )

        return None

    def get_siemplify_objects_from_raw_data(self, raw_data):
        attack_relationships = []
        attacks = []
        for attack_data in raw_data.get(OBJECT_KEY, []):
            if attack_data.get("type") == RELATIONSHIP_TYPE:
                attack_relationships.append(
                    self.build_siemplify_attack_relationship_obj(attack_data)
                )
            else:
                attacks.append(self.build_siemplify_attack_obj(attack_data))

        return attacks, attack_relationships
