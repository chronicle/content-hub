from __future__ import annotations
from .datamodels import *


class EasyVistaParser:

    def build_ticket_object(self, raw_data):

        return Ticket(
            raw_data=raw_data,
            href=raw_data.get("HREF"),
            creation_date_ut=raw_data.get("CREATION_DATE_UT"),
            end_date_ut=raw_data.get("END_DATE_UT"),
            last_update=raw_data.get("LAST_UPDATE"),
            department_path=raw_data.get("DEPARTMENT_PATH"),
            department_id=raw_data.get("DEPARTMENT_PATH"),
            catalog_request_path=raw_data.get("CATALOG_REQUEST", {}).get(
                "CATALOG_REQUEST_PATH"
            ),
            status_en=raw_data.get("STATUS", {}).get("STATUS_EN"),
            recipient_email=raw_data.get("RECIPIENT", {}).get("E_MAIL"),
            requestor_email=raw_data.get("REQUESTOR", {}).get("E_MAIL"),
            location_en=raw_data.get("LOCATION", {}).get("LOCATION_EN"),
            location_path=raw_data.get("LOCATION").get("LOCATION_PATH"),
        )

    def build_ticket_description_object(self, raw_data):

        return TicketDescription(
            raw_data=raw_data, description=raw_data.get("DESCRIPTION")
        )

    def build_ticket_comment_object(self, raw_data):

        return TicketComment(raw_data=raw_data, comment=raw_data.get("COMMENT"))

    def build_ticket_actions_object(self, raw_data):

        return TicketAction(
            raw_data=raw_data, action_label_en=raw_data.get("ACTION_LABEL_EN")
        )

    def build_ticket_attachments_object(self, raw_data):

        return TicketAttachment(
            raw_data=raw_data, document_id=raw_data.get("DOCUMENT_ID")
        )

    def build_ticket_actions_list(self, raw_data):

        return [
            self.build_ticket_actions_object(document_id)
            for document_id in raw_data.get("records")
        ]

    def build_ticket_attachments_list(self, raw_data):

        return [
            self.build_ticket_attachments_object(document_id)
            for document_id in raw_data.get("Documents")
        ]

    def build_final_object(
        self,
        general_ticket_info,
        ticket_description,
        ticket_comment,
        ticket_actions,
        ticket_attachments,
    ):

        return TicketInformation(
            general_ticket_info=general_ticket_info,
            ticket_description=ticket_description,
            ticket_comment=ticket_comment,
            ticket_actions=ticket_actions,
            ticket_attachments=ticket_attachments,
        )
