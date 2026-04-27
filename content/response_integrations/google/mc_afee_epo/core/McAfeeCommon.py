from __future__ import annotations
from soar_sdk.SiemplifyDataModel import EntityTypes
from .utils import get_entity_original_identifier


class McAfeeCommon:
    @staticmethod
    def system_match_to_entity(system, entity):
        """
        Is system matching to entity
        :param system: {SystemInformation}
        :param entity: {SiemplifyEntity}
        return: {bool}
        """
        entity_identifier = get_entity_original_identifier(entity)

        if entity.entity_type == EntityTypes.ADDRESS:
            if system.ip_address == entity_identifier:
                return True

        elif entity.entity_type == EntityTypes.HOSTNAME:
            entity_identifier = entity_identifier.lower()
            if len(entity_identifier) <= 15:
                # For shortened entities (McAfee cuts hostnames to their netbios names, aka slices after 15
                # characters and this is located in the ComputerName field
                if system.computer_name.lower() == entity_identifier:
                    return True
            else:
                # IPHostName contains the full FQDN of the machine
                # Try without the domain part (aka split by first.)
                if system.ip_host_name.split(".")[0].lower() == entity_identifier:
                    return True
                # Try the full hostname against the entity identifier
                elif system.ip_host_name.lower() == entity_identifier:
                    return True

        return False

    @staticmethod
    def filter_systems_by_entity(systems, entity):
        """
        Client side filtering by hostname or ip
        :param systems: {list} List for SystemInformation's
        :param entity: Siemplify Entity
        return: {SystemInformation}
        """
        for system in systems:
            if McAfeeCommon.system_match_to_entity(system=system, entity=entity):
                return system

        raise Exception(f"Could not find system with entity {entity}")
