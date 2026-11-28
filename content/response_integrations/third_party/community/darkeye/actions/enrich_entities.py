from __future__ import annotations

from typing import TYPE_CHECKING, Any

from TIPCommon.base.action import EntityTypesEnum
from TIPCommon.base.action.data_models import DataTable
from TIPCommon.extraction import extract_action_param
from TIPCommon.transformation import add_prefix_to_dict, construct_csv

from ..core.base_action import DarkEyeAction
from ..core.constants import (
    BREACH_HOUSE_MAX_LIMIT,
    DEFAULT_LIMIT,
    DEFAULT_MAX_PAGES,
    DEFAULT_MAX_RECORDS,
    ENRICH_ENTITIES_SCRIPT_NAME,
    ENRICHMENT_PREFIX,
    HAVEIBEENRANSOM,
    LIMIT_PARAM,
    MAX_PAGES_LIMIT,
    MAX_PAGES_PARAM,
    MAX_RECORDS_LIMIT,
    MAX_RECORDS_PARAM,
)
from ..core.data_models import EntityResult, ProductResult, Record
from ..core.exceptions import DarkEyeAllProductsFailedError, DarkEyeProductError
from ..core.utils import is_about_domain, is_email, mentions_email, normalize_domain, normalize_email

if TYPE_CHECKING:
    from typing import NoReturn

    from TIPCommon.types import Entity


SUCCESS_MESSAGE: str = "Successfully enriched the following entities using DarkEye: {}"
FOUND_MESSAGE: str = "DarkEye found records for the following entities: {}"
NOT_FOUND_MESSAGE: str = "DarkEye found no records for the following entities: {}"
TRUNCATED_MESSAGE: str = (
    "More records exist than were read for the following entities; raise the limits to read more: {}"
)
PARTIAL_MESSAGE: str = "Some products failed for the following entities: {}"
FAILED_MESSAGE: str = "Action wasn't able to enrich the following entities using DarkEye: {}"
NO_ENTITIES_MESSAGE: str = "None of the provided entities were enriched."
ERROR_MESSAGE: str = 'Error executing action "Enrich Entities".'
INVALID_NUMBER_MESSAGE: str = "'{}' must be a positive whole number."


class EnrichEntities(DarkEyeAction):
    """Enrich domain entities and user entities that are email addresses."""

    def __init__(self) -> None:
        super().__init__(ENRICH_ENTITIES_SCRIPT_NAME)
        self.error_output_message: str = ERROR_MESSAGE
        self.enriched: list[str] = []
        self.found: list[str] = []
        self.not_found: list[str] = []
        self.truncated: list[str] = []
        self.partial: list[str] = []
        self.failed: list[str] = []

    def _extract_action_parameters(self) -> None:
        self.params.max_pages = extract_action_param(self.soar_action, param_name=MAX_PAGES_PARAM, print_value=True)
        self.params.limit = extract_action_param(self.soar_action, param_name=LIMIT_PARAM, print_value=True)
        self.params.max_records = extract_action_param(self.soar_action, param_name=MAX_RECORDS_PARAM, print_value=True)

    def _validate_params(self) -> None:
        self.params.max_pages = _read_number(self.params.max_pages, MAX_PAGES_PARAM, DEFAULT_MAX_PAGES, MAX_PAGES_LIMIT)
        self.params.limit = _read_number(self.params.limit, LIMIT_PARAM, DEFAULT_LIMIT, BREACH_HOUSE_MAX_LIMIT)
        self.params.max_records = _read_number(
            self.params.max_records, MAX_RECORDS_PARAM, DEFAULT_MAX_RECORDS, MAX_RECORDS_LIMIT
        )

    def _get_entity_types(self) -> list[EntityTypesEnum]:
        return [EntityTypesEnum.DOMAIN, EntityTypesEnum.USER]

    def _perform_action(self, current_entity: Entity) -> None:
        self.data_tables = []
        identifier: str = current_entity.original_identifier
        if current_entity.entity_type == EntityTypesEnum.USER.value and not is_email(identifier):
            self.logger.info(f"Entity {identifier} is not an email address. Skipping.")
            return

        result: EntityResult = self._search(current_entity)
        current_entity.additional_properties.update(add_prefix_to_dict(result.to_enrichment(), ENRICHMENT_PREFIX))
        current_entity.is_enriched = True
        self.entities_to_update.append(current_entity)
        self.json_results[identifier] = result.to_json()

        self.enriched.append(identifier)
        (self.found if result.records else self.not_found).append(identifier)
        if result.truncated:
            self.truncated.append(identifier)
        if result.errors:
            errors: str = "; ".join(error["error"] for error in result.errors)
            self.partial.append(f"{identifier} ({errors})")
        if result.records:
            self.data_tables = [
                DataTable(
                    title=f"DarkEye: {identifier}",
                    data_table=construct_csv([record.to_table_row() for record in result.records]),
                )
            ]

    def _search(self, current_entity: Entity) -> EntityResult:
        """Query every configured product for one entity.

        Raises:
            DarkEyeAllProductsFailedError: If no product answered. An empty result would read
                as "nothing found" when nothing was searched.
        """
        identifier: str = current_entity.original_identifier
        if current_entity.entity_type == EntityTypesEnum.USER.value:
            field, term = "email", normalize_email(identifier)
        else:
            field, term = "domain", normalize_domain(identifier)
        result = EntityResult(entity=term, entity_type=field)
        for product in self.api_client.products:
            try:
                product_result: ProductResult = self._search_product(product, field, term)
            except DarkEyeProductError as error:
                self.logger.error(str(error))
                result.add_error(product, str(error))
                continue
            result.add(product, product_result)
        if not result.products:
            raise DarkEyeAllProductsFailedError(" ".join(error["error"] for error in result.errors))
        return result

    def _search_product(self, product: str, field: str, term: str) -> ProductResult:
        if product == HAVEIBEENRANSOM:
            return self.api_client.search_haveibeenransom(
                field, term, max_pages=self.params.max_pages, max_records=self.params.max_records
            )

        def is_match(record: Record, item: dict[str, Any]) -> bool:
            if field == "domain":
                return is_about_domain(record.website, record.title, term)
            fields: list[str] = [item.get(key) for key in ("post_title", "name", "website", "meta_description")]
            return mentions_email(term, *(value for value in fields if isinstance(value, str)))

        return self.api_client.search_breach_house(
            term, limit=self.params.limit, max_records=self.params.max_records, is_match=is_match
        )

    def _on_entity_failure(self, current_entity: Entity, error: Exception) -> None:
        self.data_tables = []
        self.failed.append(f"{current_entity.original_identifier} ({error})")

    def _finalize_action_on_success(self) -> None:
        messages: list[str] = []
        if self.enriched:
            messages.append(SUCCESS_MESSAGE.format(", ".join(self.enriched)))
            if self.found:
                messages.append(FOUND_MESSAGE.format(", ".join(self.found)))
            if self.not_found:
                messages.append(NOT_FOUND_MESSAGE.format(", ".join(self.not_found)))
            if self.truncated:
                messages.append(TRUNCATED_MESSAGE.format(", ".join(self.truncated)))
            if self.partial:
                messages.append(PARTIAL_MESSAGE.format(", ".join(self.partial)))
        else:
            messages.append(NO_ENTITIES_MESSAGE)
            self.result_value = False
        if self.failed:
            messages.append(FAILED_MESSAGE.format(", ".join(self.failed)))
        self.output_message = "\n".join(messages)


def _read_number(value: Any, name: str, default: int, maximum: int) -> int:  # noqa: ANN401
    """Read a positive whole number parameter. Empty means the default; larger values are capped."""
    text: str = "" if value is None else str(value).strip()
    if not text:
        return default
    if not text.isdigit() or int(text) < 1:
        raise ValueError(INVALID_NUMBER_MESSAGE.format(name))
    return min(int(text), maximum)


def main() -> NoReturn:
    EnrichEntities().run()


if __name__ == "__main__":
    main()
