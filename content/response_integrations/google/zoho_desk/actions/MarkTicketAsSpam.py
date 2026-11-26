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

from typing import NoReturn

from TIPCommon.base.action import Action
from TIPCommon.extraction import extract_action_param
from ..core import action_init
from ..core.ZohoDeskApiManager import ZohoDeskApiClient
from ..core.constants import INTEGRATION_DISPLAY_NAME, MARK_TICKET_AS_SPAM_SCRIPT_NAME


class MarkTicketAsSpam(Action[ZohoDeskApiClient]):

    def __init__(self) -> None:
        super().__init__(MARK_TICKET_AS_SPAM_SCRIPT_NAME)

    def _extract_action_parameters(self) -> None:
        self.params.ticket_id = extract_action_param(
            self.soar_action,
            param_name="Ticket ID",
            is_mandatory=True,
            print_value=True,
        )
        self.params.mark_contact = extract_action_param(
            self.soar_action,
            param_name="Mark Contact",
            print_value=True,
            input_type=bool,
        )

    def _init_api_clients(self) -> ZohoDeskApiClient:
        return action_init.create_api_client(self.soar_action)

    def _perform_action(self, _) -> None:
        self.logger.info("Fetching ticket")
        self.api_client.get_ticket(
            ticket_id=self.params.ticket_id, additional_fields=None
        )

        self.logger.info("Marking ticket as spam")
        self.api_client.mark_ticket_as_spam(
            ticket_id=self.params.ticket_id,
            mark_contact=self.params.mark_contact,
            mark_other_contact_tickets=False,
        )

        self.output_message = (
            f"Successfully marked a ticket as spam in {INTEGRATION_DISPLAY_NAME}"
        )


def main() -> NoReturn:
    MarkTicketAsSpam().run()


if __name__ == "__main__":
    main()
