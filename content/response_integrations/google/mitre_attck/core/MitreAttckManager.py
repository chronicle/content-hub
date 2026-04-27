# =====================================
#              IMPORTS                #
# =====================================
from __future__ import annotations
import requests
from .MitreAttckParser import MitreAttckParser

TARGET_KEY = "target_ref"
SOURCE_KEY = "source_ref"
USES_RELATIONSHIP = "uses"
MITIGATES_RELATIONSHIP = "mitigates"
ATTACK_PATTERN_TYPE = "attack-pattern"
COURSE_OF_ACTION = "course-of-action"
INTRUSION_SET = "intrusion-set"


# =====================================
#              CLASSES                #
# =====================================
class MitreAttckManagerError(Exception):
    """
    General Exception for Attack Framework manager
    """

    pass


class MitreAttckManager:

    def __init__(self, api_root, verify_ssl):
        self.url = api_root
        self.raw_attack_data = None
        self.session = requests.Session()
        self.session.verify = verify_ssl
        self.mitre_attack_parser = MitreAttckParser()

    @staticmethod
    def validate_response(response, error_msg="An error occurred"):
        try:
            response.raise_for_status()

        except requests.HTTPError as error:
            raise MitreAttckManagerError(
                f"{error_msg}: {error} {error.response.content}"
            )

        return True

    def get_raw_attack_data(self):
        """
        Read JSON file
        :return: {str} JSON file content
        """
        if self.raw_attack_data is None:
            response = self.session.get(self.url)
            self.validate_response(response, "Unable to load JSON file")
            self.raw_attack_data = response.json()

        return self.raw_attack_data

    def test_connectivity(self):
        """
        Get attack by ID
        :return: {bool} true if connection is successful
        """
        if self.get_raw_attack_data():
            return True
        return False

    def get_all_by_id(self, attack_id, limit=20):
        """
        Get intrusions with the type equal to INTRUSION_SET and the ID equal to identity_id
        :param attack_id: {str} The attack_id to filter
        :param limit: {int} limit the result
        :return: {list} Attack
        """
        return self.get_filtered_attacks(
            {"filter_by_id": {"attack_id": attack_id}}, limit
        )

    def get_all_where_id_in(self, ids, limit=20):
        """
        Get all the data where id in ids
        :param ids: {list} list of ids to filter
        :param limit: {int} limit the result
        :return: {list} Attack
        """
        return self.get_filtered_attacks({"filter_where_id_in": {"ids": ids}}, limit)

    def get_relationships_where_target_ref(self, target_ref, relationship_type):
        """
        Get all the Attack using filter relationship_type={relationship_type} && target_ref={attack_id}
        param target_ref: {str} The target_ref of attack
        param relationship_type: {str} The relationship type to filter. Ex. USES_RELATIONSHIP, MITIGATES_RELATIONSHIP
        :return: {list} Attack
        """
        return self.get_filtered_attacks(
            {
                "filter_by_relationship_type": {"relationship_type": relationship_type},
                "filter_by_target_ref": {"target_ref": target_ref},
            }
        )

    def get_attack_pattern_by_name(self, attack_name):
        """
        Get attack with the type equal to ATTACK_PATTERN_TYPE and the name equal to the given attack_name
        :param attack_name: {str} The name of attack
        :return: {Attack} Single attack or None
        """
        return self.get_first_or_none(
            self.get_filtered_attacks(
                {
                    "filter_by_attack_type": {"attack_type": ATTACK_PATTERN_TYPE},
                    "filter_by_name": {"attack_name": attack_name},
                }
            )
        )

    def get_attack_pattern_by_id(self, attack_id):
        """
        Get attack with the type equal to ATTACK_PATTERN_TYPE and the id equal to the given attack_id
        :param attack_id: {str} The id of attack
        :return: {Attack} Single attack or None
        """
        return self.get_first_or_none(
            self.get_filtered_attacks(
                {
                    "filter_by_attack_type": {"attack_type": ATTACK_PATTERN_TYPE},
                    "filter_by_id": {"attack_id": attack_id},
                }
            )
        )

    def get_attack_pattern_by_external_id(self, attack_external_id):
        """
        Get attack with the type equal to ATTACK_PATTERN_TYPE and the external_id equal to the given attack_external_id
        :param attack_external_id: {str} The external id of attack
        :return: {Attack} Single attack or None
        """
        return self.get_first_or_none(
            self.get_filtered_attacks(
                {
                    "filter_by_attack_type": {"attack_type": ATTACK_PATTERN_TYPE},
                    "filter_by_external_id": {"external_id": attack_external_id},
                }
            )
        )

    def get_attack_by_name(self, attack_name):
        """
        Get attack by name
        :param attack_name: {str} Attack name
        :return: {Attack} Singe attack or None
        """
        return self.get_first_or_none(
            self.get_filtered_attacks(
                {
                    "filter_by_name": {"attack_name": attack_name},
                    "filter_by_attack_type": {"attack_type": ATTACK_PATTERN_TYPE},
                }
            )
        )

    def get_attack_by_id(self, attack_id):
        """
        Get attack by ID
        :param attack_id: {str} Attack ID
        :return: {Attack} Singe attack or None
        """
        return self.get_first_or_none(
            self.get_filtered_attacks(
                {
                    "filter_by_id": {"attack_id": attack_id},
                    "filter_by_attack_type": {"attack_type": ATTACK_PATTERN_TYPE},
                }
            )
        )

    def get_attack_by_external_id(self, external_id):
        """
        Returns Attack object matching with filters or None
        Args:
            external_id: String

        Returns:
            Attack object or None
        """
        return self.get_first_or_none(
            self.get_filtered_attacks(
                {
                    "filter_by_external_id": {"external_id": external_id},
                    "filter_by_attack_type": {"attack_type": ATTACK_PATTERN_TYPE},
                }
            )
        )

    def get_filtered_attacks(self, filters, limit=500):
        """
        Get filtered attacks
        :param filters: {dict} filters to apply with their parameters
        :param limit: {int} limit the result
        :return: {list} List of attacks
        """
        attacks, attack_relationships = (
            self.mitre_attack_parser.get_siemplify_objects_from_raw_data(
                self.get_raw_attack_data()
            )
        )

        return [
            attack
            for attack in attacks + attack_relationships
            if self._filter_applier(attack, filters)
        ][:limit]

    def _filter_applier(self, attack, filters):
        """
        Filter applier.
        :param attack: {list} Attacks
        :param filters: {dict} filters to apply with their parameters
        :return: {Attack} Single attack or None
        """
        for filter_name, filter_arguments in list(filters.items()):
            filter_arguments["attack"] = attack
            if not getattr(self, filter_name)(**filter_arguments):
                return False
        return True

    @staticmethod
    def get_first_or_none(attacks):
        """
        Get first or none
        :param attacks: {list} Attacks
        :return: {Attack} Single attack or None
        """
        return attacks[0] if attacks else None

    @staticmethod
    def filter_by_external_id(attack, external_id):
        """
        Filter attack by External ID
        :param attack: {attack} Attack
        :param external_id: {str} External ID
        :return: {bool}
        """
        return (
            attack.contains_external_id(external_id)
            and attack.attack_type is not None
            and attack.external_references is not None
        )

    @staticmethod
    def filter_by_created_by_ref(attack, created_by_ref):
        """
        Filter attack by created_by_ref
        :param attack: {attack} Attack
        :param created_by_ref: {str} Attack created_by_ref
        :return: {bool}
        """
        return attack.created_by_ref == created_by_ref

    @staticmethod
    def filter_by_id(attack, attack_id):
        """
        Filter attack by ID
        :param attack: {attack} Attack
        :param attack_id: {str} Attack ID
        :return: {bool}
        """
        return (
            attack.attack_id == attack_id
            and attack.attack_type is not None
            and attack.external_references is not None
        )

    @staticmethod
    def filter_where_id_in(attack, ids):
        """
        Filter attack by ID
        :param attack: {attack} Attack
        :param ids: {list} Attack IDs to filter
        :return: {bool}
        """
        return attack.attack_id in ids

    @staticmethod
    def filter_by_target_ref(attack, target_ref):
        """
        Filter attack by target_ref
        :param attack: {attack} Attack
        :param target_ref: {str} Attack target_ref
        :return: {bool}
        """
        if not hasattr(attack, "target_ref"):
            return False

        return attack.target_ref == target_ref

    @staticmethod
    def filter_by_relationship_type(attack, relationship_type):
        """
        Filter attack by relationship_type
        :param attack: {attack} Attack
        :param relationship_type: {str} Attack relationship_type
        :return: {bool}
        """
        if not hasattr(attack, "relationship_type"):
            return False

        return attack.relationship_type == relationship_type

    @staticmethod
    def filter_by_attack_type(attack, attack_type):
        """
        Filter attack by type
        :param attack: {attack} Attack
        :param attack_type: {str} Attack type
        :return: {bool}
        """
        return attack.attack_type == attack_type

    @staticmethod
    def filter_by_name(attack, attack_name, case_sensitive=False):
        """
        Filter attack by Name
        :param attack: {attack} Attack
        :param attack_name: {str} Attack name
        :param case_sensitive: {bool} Whether the search should be case sensitive or not
        :return: {bool}
        """
        if attack.name is None or attack_name is None or attack.attack_type is None:
            return False

        return (
            attack.name == attack_name
            if case_sensitive
            else attack.name.lower() == attack_name.lower()
        )
