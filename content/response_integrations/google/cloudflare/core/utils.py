from __future__ import annotations
def get_entity_original_identifier(entity):
    """
    Helper function for getting original identifier
    Args:
        entity: Entity object
    Returns:
        str
    """
    return entity.additional_properties.get("OriginalIdentifier", entity.identifier)
