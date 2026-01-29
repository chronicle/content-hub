from __future__ import annotations

from typing import TYPE_CHECKING

from soar_sdk.SiemplifyUtils import unix_now
from TIPCommon.base.action import EntityTypesEnum
from TIPCommon.base.action.base_enrich_action import EnrichAction
from TIPCommon.base.action.data_models import DataTable
from TIPCommon.extraction import extract_action_param
from TIPCommon.transformation import add_prefix_to_dict, construct_csv
from TIPCommon.validation import ParameterValidator

from ..core.base_action import SampleAction
from ..core.constants import (
    ENRICH_ENTITY_ACTION_EXAMPLE_SCRIPT_NAME,
    SupportedEntitiesEnum,
)

if TYPE_CHECKING:
    from typing import NoReturn

    from TIPCommon.base.action.data_models import Entity
    from TIPCommon.types import SingleJson


DEFAULT_ENTITY_TYPE: str = SupportedEntitiesEnum.ALL.value

SUCCESS_MESSAGE: str = "Successfully enriched the following entities: {}"
NO_ENTITIES_MESSAGE: str = "No eligible entities were found in the scope of the Alert."


class EnrichEntityActionExample(EnrichAction, SampleAction):
    def __init__(self) -> None:
        super().__init__(ENRICH_ENTITY_ACTION_EXAMPLE_SCRIPT_NAME)
        self.enriched_entities: list[str] = []

    def _extract_action_parameters(self) -> None:
        self.params.entity_type = extract_action_param(
            self.soar_action,
            param_name="Entity Type",
            default_value=DEFAULT_ENTITY_TYPE,
            print_value=True,
        )

    def _validate_params(self) -> None:
        validator: ParameterValidator = ParameterValidator(self.soar_action)
        self.params.entity_type = validator.validate_ddl(
            param_name="Entity Type",
            value=self.params.entity_type,
            ddl_values=SupportedEntitiesEnum.values(),
            print_value=True,
        )

    def _get_entity_types(self) -> list[EntityTypesEnum]:
        return SupportedEntitiesEnum(self.params.entity_type).to_entity_type_enum_list()

    def _perform_enrich_action(self, current_entity: Entity) -> None:
        self.logger.info(f"Starting enrichment for entity {current_entity.identifier}")
        timestamp: int = unix_now()

        enrichment_data: dict[str, str] = {
            "enriched": "true",
            "timestamp": str(timestamp),
        }
        self.enrichment_data: SingleJson = add_prefix_to_dict(enrichment_data, "SampleIntegration_")
        self.entity_results: dict[str, str] = enrichment_data
        self.data_tables: DataTable = [
            DataTable(
                title=f"Sample: {current_entity.identifier}",
                data_table=construct_csv([enrichment_data]),
            )
        ]
        self.enriched_entities.append(current_entity.identifier)
        self.logger.info(f"Finished enrichment for entity {current_entity.identifier}")

    def _finalize_action_on_success(self) -> None:
        super()._finalize_action_on_success()
        if self.enriched_entities:
            self.output_message = SUCCESS_MESSAGE.format(", ".join(self.enriched_entities))
        else:
            self.output_message = NO_ENTITIES_MESSAGE
            self.result_value = False


def main() -> NoReturn:
    EnrichEntityActionExample().run()


if __name__ == "__main__":
    main()
