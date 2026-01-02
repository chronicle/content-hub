from __future__ import annotations

import json
from base64 import b64encode

from anyrun.connectors import LookupConnector
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from TIPCommon.data_models import CaseWallAttachment
from TIPCommon.extraction import extract_configuration_param
from TIPCommon.rest.soar_api import save_attachment_to_case_wall
from TIPCommon.transformation import convert_comma_separated_to_list

from ..core.config import Config
from ..core.utils import (
    convert_score,
    generate_lookup_reference,
    prepare_report_comment,
    setup_action_proxy,
)


def initialize_lookup(
    siemplify,
    token: str,
    lookup_entity: str,
    entity_identifier: str,
    lookup_depth: int,
    verify_ssl: bool,
) -> str:
    with LookupConnector(
        token,
        integration=Config.VERSION,
        proxy=setup_action_proxy(siemplify),
        verify_ssl=verify_ssl,
    ) as connector:
        report = connector.get_intelligence(
            lookup_depth=lookup_depth, **{lookup_entity: entity_identifier}
        )

        siemplify.add_comment(
            f"Lookup url: {generate_lookup_reference(lookup_entity, entity_identifier)}"
        )
        save_attachment_to_case_wall(
            siemplify,
            CaseWallAttachment(
                f"{entity_identifier[:15]}_anyrun_lookup_summary",
                ".json",
                b64encode(json.dumps(report).encode()).decode(),
                True,
            ),
        )

        return convert_score(report.get("summary"))


@output_handler
def main():
    siemplify = SiemplifyAction()
    results = []

    lookup_depth = siemplify.extract_action_param("Lookup Depth", input_type=int)

    token = extract_configuration_param(
        siemplify,
        Config.INTEGRATION_NAME,
        param_name="ANYRUN TI Lookup API KEY",
        is_mandatory=True,
    )

    verify_ssl = extract_configuration_param(
        siemplify, Config.INTEGRATION_NAME, param_name="Verify SSL", input_type=bool
    )

    if query := siemplify.extract_action_param("Query"):
        verdict = initialize_lookup(siemplify, token, "query", query, lookup_depth, verify_ssl)
        results.append(("Query", query, verdict))
    else:
        entity_identifiers = convert_comma_separated_to_list(
            siemplify.extract_action_param("Identifiers")
        )
        entity_types = convert_comma_separated_to_list(siemplify.extract_action_param("Types"))

        if not any([entity_identifiers, entity_types]):
            siemplify.end(
                "At least one entity type and entity identifiers must be specified",
                False,
                EXECUTION_STATE_FAILED,
            )

        for entity_type, entity_identifier in zip(entity_types, entity_identifiers):
            if lookup_entity := Config.ENTITIES.get(entity_type.lower()):
                verdict = initialize_lookup(
                    siemplify, token, lookup_entity, entity_identifier, lookup_depth, verify_ssl
                )
                siemplify.LOGGER.info(
                    "Entity: entity_identifier was lookuped. "
                    "Json summary attached to the case wall."
                )
                results.append((entity_type, entity_identifier, verdict))
            else:
                siemplify.LOGGER.info(f"Recieved not supported entity type: {entity_type}")
                results.append((entity_type, entity_identifier, "Not supported entity"))

    siemplify.add_comment(prepare_report_comment(results))
    siemplify.end("Intelligence is successfully ended.", False, EXECUTION_STATE_COMPLETED)


if __name__ == "__main__":
    main()
