import json
import logging
from typing import Optional, Union, List, Dict, Any
from TIPCommon.rest.soar_api import (
    get_installed_integrations_of_environment,
    execute_manual_action,
    get_action_result_by_id,
    get_env_action_def_files
)

logger = logging.getLogger(__name__)


def get_action_result(siemplify, result_id: str) -> Dict[str, Any]:
    """Gets the action execution result by its ID.

    Args:
        siemplify: ChronicleSOAR/SiemplifyAction object.
        result_id (str): The ID of the action result.

    Returns:
        Dict[str, Any]: JSON API response dictionary.
    """
    response = get_action_result_by_id(chronicle_soar=siemplify, result_id=result_id)
    return response.json()


def execute_orchestrated_action(
    siemplify,
    integration_name: str,
    action_name: str,
    action_parameters: Dict[str, Any],
    *,
    instance_mode: str = "auto",
    explicit_instance_id: Optional[str] = None,
    inherit_alert_entities: bool = True,
    target_entities: Optional[List[Any]] = None,
    action_provider: str = "Scripts"
) -> Dict[str, Any]:
    """Resolves correct integration instance and triggers the manual action.

    Args:
        siemplify: ChronicleSOAR/SiemplifyAction object.
        integration_name (str): Identifier of the integration (e.g. 'GoogleThreatIntelligence').
        action_name (str): Name of the action to execute (e.g. 'Google Threat Intelligence_Ping').
        action_parameters (Dict[str, Any]): Dictionary of action parameters.
        instance_mode (str): Instance selection mode ('auto', 'shared', 'explicit'). Defaults to 'auto'.
        explicit_instance_id (Optional[str]): Explicit instance ID to use if mode is 'explicit'.
        inherit_alert_entities (bool): If True, passes alert entities (or target_entities) to the action.
        target_entities (Optional[List[Any]]): Custom list of SDK entity objects to pass. If None, inherits from alert.
        action_provider (str): Action provider name. Defaults to 'Scripts'.

    Returns:
        Dict[str, Any]: JSON API response dictionary.
    """
    # 1. Resolve integration instance
    instance_id = None
    if instance_mode == "explicit":
        if not explicit_instance_id:
            raise ValueError("explicit_instance_id must be provided when instance_mode is 'explicit'")
        instance_id = explicit_instance_id
    else:
        # Determine environment to query
        env = "Shared Instances" if instance_mode == "shared" else (
            getattr(siemplify.current_alert, "environment", None) or siemplify.environment
        )
        instances = get_installed_integrations_of_environment(siemplify, env, integration_name)
        if not instances and instance_mode == "auto":
            # Fall back to shared
            instances = get_installed_integrations_of_environment(siemplify, "Shared Instances", integration_name)
        
        if not instances:
            raise RuntimeError(f"Could not find any installed instance for integration '{integration_name}'")
        instance_id = instances[0].identifier

    # 2. Extract Alert / Case details
    case_id = siemplify.case_id
    alert_group_identifier = siemplify.current_alert.alert_group_identifier
    
    # 3. Handle entities
    payload_entities = []
    scope = "Alert"
    if inherit_alert_entities:
        entities_to_map = target_entities if target_entities is not None else siemplify.current_alert.entities
        for ent in entities_to_map:
            payload_entities.append({
                "caseId": case_id,
                "identifier": ent.identifier,
                "entityType": ent.entity_type,
                "isInternal": ent.is_internal,
                "isSuspicious": ent.is_suspicious,
                "isArtifact": ent.is_artifact,
                "isEnriched": ent.is_enriched,
                "isVulnerable": ent.is_vulnerable,
                "isPivot": ent.is_pivot,
                "environment": getattr(ent, "environment", None) or siemplify.current_alert.environment
            })
    
    # Fetch action definitions and populate default parameter values if missing
    try:
        action_defs = get_env_action_def_files(siemplify)
        matching_action_def = None
        if isinstance(action_defs, list):
            for action_def in action_defs:
                if (isinstance(action_def, dict) and
                        action_def.get("IntegrationIdentifier") == integration_name and 
                        action_def.get("Name") == action_name):
                    matching_action_def = action_def
                    break
        
        if matching_action_def:
            for param in matching_action_def.get("Parameters", []):
                param_name = param.get("Name")
                default_val = param.get("DefaultValue")
                is_mandatory = param.get("IsMandatory", False)
                
                if param_name:
                    if param_name not in action_parameters:
                        # If mandatory and no default value is defined, raise exception
                        if is_mandatory and (default_val is None or default_val == ""):
                            raise ValueError(f"Mandatory parameter '{param_name}' is missing for action '{action_name}'.")
                        
                        # Populate with default value if it exists, otherwise empty string
                        if default_val is not None:
                            action_parameters[param_name] = default_val
                        else:
                            action_parameters[param_name] = ""
                    else:
                        # Param is present, check if it's empty and mandatory
                        param_value = action_parameters[param_name]
                        if is_mandatory and (param_value is None or param_value == ""):
                            raise ValueError(f"Mandatory parameter '{param_name}' has an empty value for action '{action_name}'.")
    except ValueError as ve:
        # Mandatory parameter missing should propagate as an error
        logger.error(str(ve))
        raise
    except Exception as e:
        logger.warning(
            f"Failed to fetch action definitions to populate default parameters: {e}. "
            f"Proceeding with provided action parameters."
        )

    action_properties = {
        "ScriptName": action_name,
        "ScriptParametersEntityFields": json.dumps({k: str(v) for k, v in action_parameters.items()}),
        "IntegrationInstance": instance_id
    }
    
    # 4. Trigger manual action
    response = execute_manual_action(
        chronicle_soar=siemplify,
        case_id=case_id,
        action_name=action_name,
        action_properties=action_properties,
        alert_group_identifiers=[alert_group_identifier],
        scope=scope,
        target_entities=payload_entities,
        is_predefined_scope=len(payload_entities) > 0,
        action_provider=action_provider
    )
    return response.json()
