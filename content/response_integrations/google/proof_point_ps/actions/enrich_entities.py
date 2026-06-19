# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from SiemplifyDataModel import EntityTypes
from SiemplifyUtils import (
    add_prefix_to_dict,
    dict_to_flat,
    get_domain_from_entity,
)
from TIPCommon.base.action import EntityTypesEnum

from ..core.base_action import BaseProofPointPSAction
from ..core.constants import ENRICH_ACTION_NAME

if TYPE_CHECKING:
    from TIPCommon.types import Entity


def is_valid_email(email: str) -> bool:
    """Validate if a string is a valid email format.

    Args:
        email: The string to validate.

    Returns:
        True if valid email, False otherwise.

    """
    return (
        re.match(
            r"^[_a-z0-9-]+(\.[_a-z0-9-]+)*@[a-z0-9-]+(\.[a-z0-9-]+)*(\.[a-z]{2,4})$",
            email,
            re.IGNORECASE,
        )
        is not None
    )


class EnrichEntities(BaseProofPointPSAction):
    """Enrich entities with ProofPoint PS integration."""

    def __init__(self) -> None:
        super().__init__(ENRICH_ACTION_NAME)
        self.successful_entities: list[Entity] = []
        self.failed_entities: list[Entity] = []
        self.json_results: dict[str, list[dict]] = {}

    def _get_entity_types(self) -> list[EntityTypesEnum]:
        """Get the supported entity types for this action.

        Returns:
            A list of EntityTypesEnum.

        """
        return [EntityTypesEnum.HOST_NAME, EntityTypesEnum.USER]

    def _perform_action(self, current_entity: Entity | None) -> None:
        """Enrich a single host/user entity from quarantined records.

        Args:
            current_entity: The entity to enrich.

        """
        if current_entity is None:
            return

        folders = ["Quarantine", "Spam", "Virus"]
        records = []

        if current_entity.entity_type == EntityTypes.HOSTNAME:
            domain = get_domain_from_entity(current_entity)
            self.logger.info(
                f"Hostname entity={current_entity.identifier}, extracted domain={domain}"
            )
            for folder in folders:
                try:
                    res = self.api_client.search(sender=f"@{domain}", folder=folder)
                    self.logger.info(
                        f"Sender search for @{domain} in {folder} found {len(res)} records"
                    )
                    records.extend(res)
                except Exception:
                    self.logger.exception(
                        f"Sender search failed for @{domain} in {folder}"
                    )
                try:
                    res = self.api_client.search(recipient=f"@{domain}", folder=folder)
                    self.logger.info(
                        f"Recipient search for @{domain} in {folder} found {len(res)} records"
                    )
                    records.extend(res)
                except Exception:
                    self.logger.exception(
                        f"Recipient search failed for @{domain} in {folder}"
                    )
        elif current_entity.entity_type == EntityTypes.USER and is_valid_email(
            current_entity.identifier
        ):
            for folder in folders:
                try:
                    records.extend(
                        self.api_client.search(
                            sender=current_entity.identifier, folder=folder
                        )
                    )
                except Exception:
                    self.logger.exception(
                        f"Sender search failed for {current_entity.identifier} in {folder}"
                    )
                try:
                    records.extend(
                        self.api_client.search(
                            recipient=current_entity.identifier, folder=folder
                        )
                    )
                except Exception:
                    self.logger.exception(
                        f"Recipient search failed for {current_entity.identifier} in {folder}"
                    )

        if records:
            for index, record_obj in enumerate(records):
                record = record_obj.to_json()
                if "dlpviolation" in record:
                    del record["dlpviolation"]

                if "messagestatus" in record:
                    del record["messagestatus"]

                flat_record = dict_to_flat(record)
                flat_record = add_prefix_to_dict(flat_record, index)
                flat_record = add_prefix_to_dict(flat_record, "ProofPointPS")
                current_entity.additional_properties.update(flat_record)

            self.json_results[current_entity.identifier] = [
                record.to_json() for record in records
            ]
            self.successful_entities.append(current_entity)
            self.entities_to_update.append(current_entity)
        else:
            self.failed_entities.append(current_entity)

    def _finalize_action_on_success(self) -> None:
        """Finalizes action execution by preparing output messages."""
        if self.successful_entities:
            successful_names = ", ".join(e.identifier for e in self.successful_entities)
            self.output_message = (
                f"Successfully enriched the following entities using "
                f"Proofpoint Email Protection: {successful_names}"
            )
            if self.failed_entities:
                failed_names = ", ".join(e.identifier for e in self.failed_entities)
                self.output_message += (
                    f"\nAction wasn't able to enrich the following entities "
                    f"using Proofpoint Email Protection: {failed_names}"
                )
            
            
        else:
            self.json_results = []
            self.output_message = "None of the provided entities were enriched."
            self.result_value = False


def main() -> None:
    EnrichEntities().run()


if __name__ == "__main__":
    main()
