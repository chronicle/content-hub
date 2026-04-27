from __future__ import annotations
from TIPCommon import dict_to_flat, add_prefix_to_dict


class BaseModel:
    """
    Base model for inheritance
    """

    def __init__(self, raw_data):
        self.raw_data = raw_data

    def to_json(self):
        return self.raw_data

    def to_csv(self):
        return dict_to_flat(self.to_json())

    def to_enrichment_data(self, prefix=None):
        data = dict_to_flat(self.raw_data)
        return add_prefix_to_dict(data, prefix) if prefix else data


class Ticket:
    def __init__(
        self,
        raw_data=None,
        location_path=None,
        location_en=None,
        href=None,
        creation_date_ut=None,
        end_date_ut=None,
        last_update=None,
        department_path=None,
        department_id=None,
        catalog_request_path=None,
        status_en=None,
        recipient_email=None,
        requestor_email=None,
    ):
        self.raw_data = raw_data
        self.href = href
        self.creation_date_ut = creation_date_ut
        self.end_date_ut = end_date_ut
        self.last_update = last_update
        self.department_path = department_path
        self.department_id = department_id
        self.catalog_request_path = catalog_request_path
        self.status_en = status_en
        self.recipient_email = recipient_email
        self.requestor_email = requestor_email
        self.location_en = location_en
        self.location_path = location_path

    def to_json(self):
        return self.raw_data

    def to_flat_dict(self):
        return dict_to_flat(self.to_dict())


class TicketDescription:
    def __init__(self, raw_data=None, description=None):
        self.raw_data = raw_data
        self.description = description

    def to_json(self):
        return self.raw_data

    def to_flat_dict(self):
        return dict_to_flat(self.to_dict())


class TicketComment:
    def __init__(self, raw_data=None, comment=None):
        self.raw_data = raw_data
        self.comment = comment

    def to_json(self):
        return self.raw_data

    def to_flat_dict(self):
        return dict_to_flat(self.to_dict())


class TicketAttachment:
    def __init__(self, raw_data=None, document_id=None):
        self.raw_data = raw_data
        self.document_id = document_id

    def to_json(self):
        return self.raw_data

    def to_flat_dict(self):
        return dict_to_flat(self.to_dict())


class TicketAction:
    def __init__(self, raw_data=None, action_label_en=None):
        self.raw_data = raw_data
        self.action_label_en = action_label_en

    def to_json(self):
        return self.raw_data

    def to_flat_dict(self):
        return dict_to_flat(self.to_dict())


class TicketInformation:
    def __init__(
        self,
        general_ticket_info=None,
        ticket_description=None,
        ticket_comment=None,
        ticket_actions=None,
        ticket_attachments=None,
    ):
        self.general_ticket_info = general_ticket_info
        self.ticket_description = ticket_description
        self.ticket_comment = ticket_comment
        self.ticket_actions = ticket_actions
        self.ticket_attachments = ticket_attachments

    def to_json(self):

        ticket_actions_json = [action.to_json() for action in self.ticket_actions]
        ticket_attachments_json = [
            attachment.to_json() for attachment in self.ticket_attachments
        ]

        final_object = {
            "General": self.general_ticket_info.to_json(),
            "Ticket Description": self.ticket_description.to_json(),
            "Ticket Comments": self.ticket_comment.to_json(),
            "Ticket Actions": ticket_actions_json,
            "Ticket Attachments": ticket_attachments_json,
        }

        return final_object

    def to_table(self):

        ticket_actions_list = [action.action_label_en for action in self.ticket_actions]
        ticket_attachments_json_list = [
            attachment.document_id for attachment in self.ticket_attachments
        ]

        return {
            "HREF": self.general_ticket_info.href,
            "DESCRIPTION ": self.ticket_description.description,
            "COMMENT ": self.ticket_comment.comment,
            "CREATION_DATE_UT": self.general_ticket_info.creation_date_ut,
            "END_DATE_UT ": self.general_ticket_info.end_date_ut,
            "LAST_UPDATE ": self.general_ticket_info.last_update,
            "DEPARTMENT_PATH": self.general_ticket_info.department_path,
            "DEPARTMENT_ID ": self.general_ticket_info.department_id,
            "CATALOG_REQUEST": self.general_ticket_info.catalog_request_path,
            "STATUS": self.general_ticket_info.status_en,
            "RECIPIENT_EMAIL": self.general_ticket_info.recipient_email,
            "REQUESTOR_EMAIL ": self.general_ticket_info.requestor_email,
            "LOCATION ": self.general_ticket_info.location_en,
            "LOCATION_PATH ": self.general_ticket_info.location_path,
            "ATTACHMENTS ": ticket_attachments_json_list,
            "ACTIONS ": ticket_actions_list,
        }
