"""Calculate Risk Score and other fields for Alert filtration Action."""

from __future__ import annotations

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

from ..core.constants import (
    CHOKE_POINT_SCORE_FIELD_NAME,
    COMPROMISE_RISK_SCORE_FIELD_NAME,
    ENRICHED_ENTITY_ID_FIELD,
    ENTITY_ID_FIELD,
    PREFIX_PARAMETER_FOR_ENTITY_ID,
    PREFIX_PARAMETER_FOR_LABELS,
    SUPPORTED_ENTITY_TYPES,
)
from ..core.utils import convert_string, convert_to_numeric, string_to_list

SCORE_MAPPINGS = {
    "Is Critical Asset": {
        "Disabled": 0,
        "Low": 0.15,
        "Default": 0.2,
        "High": 0.3,
    },
    "Predefined Admin": {
        "Disabled": 0,
        "Low": 0.05,
        "Default": 0.1,
        "High": 0.3,
    },
    "Highly Privileged": {
        "Disabled": 0,
        "Low": 0.05,
        "Default": 0.1,
        "High": 0.2,
    },
    "User without MFA": {
        "Disabled": 0,
        "Low": 0.05,
        "Default": 0.1,
        "High": 0.2,
    },
    CHOKE_POINT_SCORE_FIELD_NAME: {
        "Low": 0.002,
        "Default": 0.004,
        "High": 0.006,
    },
    COMPROMISE_RISK_SCORE_FIELD_NAME: {
        "Low": 0.002,
        "Default": 0.004,
        "High": 0.006,
    },
    "AD Risk to Domain": {
        "Disabled": 0,
        "Low": 0.05,
        "Default": 0.1,
        "High": 0.2,
    },
    "AD Risky Principals": {
        "Disabled": 0,
        "Low": 0.05,
        "Default": 0.1,
        "High": 0.2,
    },
    "AD Admins And DCs": {
        "Disabled": 0,
        "Low": 0.1,
        "Default": 0.15,
        "High": 0.2,
    },
}

RISK_MAPPING = {
    "NONE": 0,
    "INFORMATIVE": 1,
    "LOW": 2,
    "MEDIUM": 3,
    "HIGH": 4,
    "CRITICAL": 5,
}
REVERSE_RISK_MAPPING = {v: k for k, v in RISK_MAPPING.items()}


def calculate_score(data_properties, score_components, event_type=None):
    """
    Calculate a score based on a set of components.

    Args:
        data_properties (dict): A dictionary of event or entity properties
        score_components (list): A list of tuples, where each tuple contains the following:
            1. The name of the field to check
            2. The score to add if the field matches
            3. The value to check in the field (optional)

    Returns:
        int: The calculated score
    """
    score = 1
    for component in score_components:
        field_name, score_value = component[:2]
        value_to_check = component[2] if len(component) == 3 else "TRUE"

        if event_type is not None:
            field_value = data_properties.get(
                PREFIX_PARAMETER_FOR_LABELS.format(event_type, field_name), ""
            )
        else:
            field_value = data_properties.get(PREFIX_PARAMETER_FOR_ENTITY_ID.format(field_name), "")

        if field_value == value_to_check:
            score += score_value
    return score


def calculate_risk_score(event_type, event_properties, configured_params):
    """
    Calculate risk score and other fields for Alert filtration Action based on event properties.

    Args:
        event_properties (dict): A dictionary of event properties

    Returns:
        dict: A dictionary containing the calculated risk score and other fields
    """
    base_risk_score = convert_to_numeric(event_properties.get("detection_outcomes_risk_score", "0"))
    if base_risk_score == 0:
        base_risk_score = 45

        if event_properties.get("event_principal_namespace") == "kube-system":
            base_risk_score += 35
    choke_point_score_value = SCORE_MAPPINGS[CHOKE_POINT_SCORE_FIELD_NAME][
        configured_params.get("choke_point_score")
    ] * convert_string(
        event_properties.get(
            PREFIX_PARAMETER_FOR_LABELS.format(event_type, "Choke Point Score"),
            "0",
        )
    )
    compromise_risk_score_value = SCORE_MAPPINGS[COMPROMISE_RISK_SCORE_FIELD_NAME][
        configured_params.get("compromise_risk_score")
    ] * convert_string(
        event_properties.get(
            PREFIX_PARAMETER_FOR_LABELS.format(event_type, "Compromise Risk Score"),
            "0",
        )
    )
    impact_score_components = [
        (
            "Is Critical Asset",
            SCORE_MAPPINGS["Is Critical Asset"][configured_params.get("is_critical_asset")],
        ),
        (
            "Predefined Admin",
            SCORE_MAPPINGS["Predefined Admin"][configured_params.get("is_predefined_admin")],
        ),
        (
            "Highly Privileged",
            SCORE_MAPPINGS["Highly Privileged"][configured_params.get("is_highly_privileged")],
        ),
        (
            "AD Risk to Domain",
            SCORE_MAPPINGS["AD Risk to Domain"][configured_params.get("ad_risk_to_domain")],
        ),
        (
            "AD Risky Principals",
            SCORE_MAPPINGS["AD Risky Principals"][configured_params.get("ad_risky_principals")],
        ),
        (
            "AD Admins And DCs",
            SCORE_MAPPINGS["AD Admins And DCs"][configured_params.get("ad_admins_and_dcs")],
        ),
    ]

    impact_score = calculate_score(event_properties, impact_score_components, event_type)
    impact_score += choke_point_score_value
    impact_score = min(impact_score, 1.7)
    probability_score_components = [
        (
            "User without MFA",
            SCORE_MAPPINGS["User without MFA"][configured_params.get("user_without_mfa")],
        )
    ]

    probability_score = calculate_score(event_properties, probability_score_components, event_type)
    probability_score += compromise_risk_score_value

    calculated_risk_score = base_risk_score * probability_score * impact_score
    risk_score = min(calculated_risk_score, 100)
    labels_string = event_properties.get(
        PREFIX_PARAMETER_FOR_LABELS.format(event_type, "Labels"), ""
    )
    labels = string_to_list(labels_string) if labels_string != "" else []

    return {
        "base_risk_score": base_risk_score,
        "risk_score": risk_score,
        "is_critical_asset": convert_string(
            event_properties.get(
                PREFIX_PARAMETER_FOR_LABELS.format(event_type, "Is Critical Asset"), ""
            )
        ),
        "is_highly_privileged": convert_string(
            event_properties.get(
                PREFIX_PARAMETER_FOR_LABELS.format(event_type, "Highly Privileged"), ""
            )
        ),
        "is_predefined_admin": convert_string(
            event_properties.get(
                PREFIX_PARAMETER_FOR_LABELS.format(event_type, "Predefined Admin"), ""
            )
        ),
        "user_without_mfa": convert_string(
            event_properties.get(
                PREFIX_PARAMETER_FOR_LABELS.format(event_type, "User without MFA"), ""
            )
        ),
        "compromised_choke_point_score_level": convert_string(
            event_properties.get(
                PREFIX_PARAMETER_FOR_LABELS.format(event_type, CHOKE_POINT_SCORE_FIELD_NAME),
                "",
            )
        ),
        "compromised_risk_score_level": convert_string(
            event_properties.get(
                PREFIX_PARAMETER_FOR_LABELS.format(event_type, COMPROMISE_RISK_SCORE_FIELD_NAME),
                "",
            )
        ),
        "compromised_choke_point_score": convert_string(
            event_properties.get(
                PREFIX_PARAMETER_FOR_LABELS.format(event_type, "Choke Point Score"), "0"
            )
        ),
        "compromised_risk_score": convert_string(
            event_properties.get(
                PREFIX_PARAMETER_FOR_LABELS.format(event_type, "Compromise Risk Score"),
                "0",
            )
        ),
        "labels": labels,
    }


def calculate_risk_score_for_entity(entity_properties, configured_params):
    """
    Calculate a risk score for an entity, given its properties.

    Args:
        entity_properties (dict): A dictionary of entity properties

    Returns:
        dict: A dictionary containing the calculated risk score and other fields
    """
    base_risk_score = 45
    choke_point_score_value = SCORE_MAPPINGS[CHOKE_POINT_SCORE_FIELD_NAME][
        configured_params.get("choke_point_score")
    ] * convert_string(
        entity_properties.get(
            PREFIX_PARAMETER_FOR_ENTITY_ID.format("Choke Point Score"),
            "0",
        )
    )
    compromise_risk_score_value = SCORE_MAPPINGS[COMPROMISE_RISK_SCORE_FIELD_NAME][
        configured_params.get("compromise_risk_score")
    ] * convert_string(
        entity_properties.get(
            PREFIX_PARAMETER_FOR_ENTITY_ID.format("Compromise Risk Score"),
            "0",
        )
    )
    impact_score_components = [
        (
            "Is Critical Asset",
            SCORE_MAPPINGS["Is Critical Asset"][configured_params.get("is_critical_asset")],
        ),
        (
            "Predefined Admin",
            SCORE_MAPPINGS["Predefined Admin"][configured_params.get("is_predefined_admin")],
        ),
        (
            "Highly Privileged",
            SCORE_MAPPINGS["Highly Privileged"][configured_params.get("is_highly_privileged")],
        ),
        (
            "AD Risk to Domain",
            SCORE_MAPPINGS["AD Risk to Domain"][configured_params.get("ad_risk_to_domain")],
        ),
        (
            "AD Risky Principals",
            SCORE_MAPPINGS["AD Risky Principals"][configured_params.get("ad_risky_principals")],
        ),
        (
            "AD Admins And DCs",
            SCORE_MAPPINGS["AD Admins And DCs"][configured_params.get("ad_admins_and_dcs")],
        ),
    ]

    impact_score = calculate_score(entity_properties, impact_score_components)
    impact_score += choke_point_score_value
    impact_score = min(impact_score, 1.7)

    probability_score_components = [
        (
            "User without MFA",
            SCORE_MAPPINGS["User without MFA"][configured_params.get("user_without_mfa")],
        )
    ]
    probability_score = calculate_score(entity_properties, probability_score_components)
    probability_score += compromise_risk_score_value

    calculated_risk_score = base_risk_score * probability_score * impact_score
    risk_score = min(calculated_risk_score, 100)

    labels_string = entity_properties.get(PREFIX_PARAMETER_FOR_ENTITY_ID.format("Labels"), "")
    labels = string_to_list(labels_string) if labels_string != "" else []

    return {
        "base_risk_score": base_risk_score,
        "risk_score": risk_score,
        "is_critical_asset": convert_string(
            entity_properties.get(PREFIX_PARAMETER_FOR_ENTITY_ID.format("Is Critical Asset"), "")
        ),
        "is_highly_privileged": convert_string(
            entity_properties.get(PREFIX_PARAMETER_FOR_ENTITY_ID.format("Highly Privileged"), "")
        ),
        "is_predefined_admin": convert_string(
            entity_properties.get(PREFIX_PARAMETER_FOR_ENTITY_ID.format("Predefined Admin"), "")
        ),
        "user_without_mfa": convert_string(
            entity_properties.get(PREFIX_PARAMETER_FOR_ENTITY_ID.format("User without MFA"), "")
        ),
        "compromised_choke_point_score_level": convert_string(
            entity_properties.get(
                PREFIX_PARAMETER_FOR_ENTITY_ID.format(CHOKE_POINT_SCORE_FIELD_NAME),
                "",
            )
        ),
        "compromised_risk_score_level": convert_string(
            entity_properties.get(
                PREFIX_PARAMETER_FOR_ENTITY_ID.format(COMPROMISE_RISK_SCORE_FIELD_NAME),
                "",
            )
        ),
        "compromised_choke_point_score": convert_string(
            entity_properties.get(PREFIX_PARAMETER_FOR_ENTITY_ID.format("Choke Point Score"), "0")
        ),
        "compromised_risk_score": convert_string(
            entity_properties.get(
                PREFIX_PARAMETER_FOR_ENTITY_ID.format("Compromise Risk Score"),
                "0",
            )
        ),
        "labels": labels,
    }


def generate_alert_json(event_json):
    """Generate an alert JSON object from a dictionary of event properties.

    Args:
        event_json (dict): A dictionary where keys are entity IDs and values are
            dictionaries of event properties.

    Returns:
        dict: A dictionary containing the aggregated risk scores and other
            properties for each entity.
    """
    aggregated_values = {
        "base_risk_score": 0,
        "risk_score": 0,
        "is_critical_asset": False,
        "is_highly_privileged": False,
        "is_predefined_admin": False,
        "user_without_mfa": False,
        "compromised_risk_score_level": RISK_MAPPING["NONE"],
        "compromised_risk_score": 0,
        "compromised_choke_point_score_level": RISK_MAPPING["NONE"],
        "compromised_choke_point_score": 0,
        "labels": set(),
    }

    for event_properties in event_json.values():
        aggregated_values["base_risk_score"] = max(
            aggregated_values["base_risk_score"],
            int(event_properties.get("base_risk_score", 0)),
        )
        aggregated_values["risk_score"] = max(
            aggregated_values["risk_score"],
            int(event_properties.get("risk_score", 0)),
        )
        aggregated_values["compromised_choke_point_score"] = max(
            aggregated_values["compromised_choke_point_score"],
            int(event_properties.get("compromised_choke_point_score", 0)),
        )
        aggregated_values["compromised_risk_score"] = max(
            aggregated_values["compromised_risk_score"],
            int(event_properties.get("compromised_risk_score", 0)),
        )

        aggregated_values["is_critical_asset"] = aggregated_values[
            "is_critical_asset"
        ] or event_properties.get("is_critical_asset", False)
        aggregated_values["is_highly_privileged"] = aggregated_values[
            "is_highly_privileged"
        ] or event_properties.get("is_highly_privileged", False)
        aggregated_values["is_predefined_admin"] = aggregated_values[
            "is_predefined_admin"
        ] or event_properties.get("is_predefined_admin", False)
        aggregated_values["user_without_mfa"] = aggregated_values[
            "user_without_mfa"
        ] or event_properties.get("user_without_mfa", False)

        aggregated_values["compromised_risk_score_level"] = max(
            aggregated_values["compromised_risk_score_level"],
            RISK_MAPPING.get(
                event_properties.get("compromised_risk_score_level", "NONE"),
                RISK_MAPPING["NONE"],
            ),
        )
        aggregated_values["compromised_choke_point_score_level"] = max(
            aggregated_values["compromised_choke_point_score_level"],
            RISK_MAPPING.get(
                event_properties.get("compromised_choke_point_score_level", "NONE"),
                RISK_MAPPING["NONE"],
            ),
        )

        aggregated_values["labels"].update(event_properties.get("labels", []) or [])

    aggregated_values["labels"] = ",".join(str(label) for label in aggregated_values["labels"])

    # Convert the scores back to the original Enum value
    aggregated_values["compromised_choke_point_score_level"] = REVERSE_RISK_MAPPING[
        aggregated_values["compromised_choke_point_score_level"]
    ]
    aggregated_values["compromised_risk_score_level"] = REVERSE_RISK_MAPPING[
        aggregated_values["compromised_risk_score_level"]
    ]
    return aggregated_values


def collect_action_parameters(siemplify):
    """
    Collect action parameters from SiemplifyAction instance.

    Args:
        siemplify (SiemplifyAction): An instance of SiemplifyAction.

    Returns:
        dict: A dictionary containing the action parameters.
    """
    is_critical_asset = siemplify.extract_action_param(
        "Is Critical Asset", is_mandatory=False, input_type=str, default_value="Disabled"
    )
    predefined_admin = siemplify.extract_action_param(
        "Predefined Admin", is_mandatory=False, input_type=str, default_value="Disabled"
    )
    highly_privileged = siemplify.extract_action_param(
        "Highly Privileged", is_mandatory=False, input_type=str, default_value="Disabled"
    )
    ad_risk_to_domain = siemplify.extract_action_param(
        "AD Risk to Domain", is_mandatory=False, input_type=str, default_value="Disabled"
    )
    ad_risky_principals = siemplify.extract_action_param(
        "AD Risky Principals", is_mandatory=False, input_type=str, default_value="Disabled"
    )
    ad_admins_and_dcs = siemplify.extract_action_param(
        "AD Admins And DCs", is_mandatory=False, input_type=str, default_value="Disabled"
    )
    user_without_mfa = siemplify.extract_action_param(
        "User without MFA", is_mandatory=False, input_type=str, default_value="Disabled"
    )
    choke_point_score = siemplify.extract_action_param(
        "Choke Point Score", is_mandatory=False, input_type=str, default_value="Default"
    )
    compromise_risk_score = siemplify.extract_action_param(
        "Compromise Risk Score", is_mandatory=False, input_type=str, default_value="Default"
    )

    configured_params = {
        "is_critical_asset": is_critical_asset,
        "is_predefined_admin": predefined_admin,
        "is_highly_privileged": highly_privileged,
        "ad_risk_to_domain": ad_risk_to_domain,
        "ad_risky_principals": ad_risky_principals,
        "ad_admins_and_dcs": ad_admins_and_dcs,
        "user_without_mfa": user_without_mfa,
        "choke_point_score": choke_point_score,
        "compromise_risk_score": compromise_risk_score,
    }

    siemplify.LOGGER.info(f"Configured Params: {configured_params}")
    return configured_params


@output_handler
def main():
    """Generate a JSON object mapping between entity ID and its details."""
    result_value = False
    output_message = ""
    status = EXECUTION_STATE_FAILED
    entity_json = {}

    siemplify = SiemplifyAction()
    events = siemplify.current_alert.security_events
    entities = siemplify.target_entities
    entities = [entity for entity in entities if entity.entity_type in SUPPORTED_ENTITY_TYPES]
    try:
        configured_params = collect_action_parameters(siemplify)

        for event in events:
            event_properties = event.additional_properties

            entity_id_map = {
                "asset": event_properties.get(ENTITY_ID_FIELD.format("asset")),
                "user": event_properties.get(ENTITY_ID_FIELD.format("user")),
            }

            for entity_type, entity_id in entity_id_map.items():
                if entity_id is None:
                    continue

                is_xm_cyber_entity = event_properties.get(
                    PREFIX_PARAMETER_FOR_LABELS.format(entity_type, "Entity Type")
                )

                if not is_xm_cyber_entity:
                    continue

                entity_json[entity_id] = calculate_risk_score(
                    entity_type, event_properties, configured_params
                )

        for entity in entities:
            xm_cyber_identifier = entity.additional_properties.get(ENRICHED_ENTITY_ID_FIELD)
            is_xm_cyber_entity = entity.additional_properties.get(
                PREFIX_PARAMETER_FOR_ENTITY_ID.format("Entity Type")
            )

            if not xm_cyber_identifier or not is_xm_cyber_entity:
                continue

            entity_json[xm_cyber_identifier] = calculate_risk_score_for_entity(
                entity.additional_properties, configured_params
            )
        if not entity_json:
            output_message = "No XM Cyber entity details found in the alert events/entities."
        else:
            # Create JSON object final
            final_alert_json = generate_alert_json(entity_json)
            output_message = (
                f"Successfully created Alert JSON object from the following entities: "
                f"{list(entity_json.keys())}"
            )
            siemplify.result.add_result_json(final_alert_json)

        status = EXECUTION_STATE_COMPLETED
        result_value = True
    except Exception as e:
        error_message = str(e)
        output_message = f"Failed to create Alert JSON object! Error: {error_message}"
        status = EXECUTION_STATE_FAILED

    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")

    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
