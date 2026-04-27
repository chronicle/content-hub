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


class BlockedEntitiesObject(BaseModel):

    def __init__(self, raw_data, senders, urls, hashes):
        super(BlockedEntitiesObject, self).__init__(raw_data)
        self.senders = senders
        self.urls = urls
        self.hashes = hashes


class EmailObject(BaseModel):

    def __init__(
        self,
        raw_data,
        mail_unique_id,
        email_value_data,
        mailbox,
        mail_message_delivery_time,
    ):
        super(EmailObject, self).__init__(raw_data)
        self.mail_unique_id = mail_unique_id
        self.email_value_data = email_value_data
        self.mailbox = mailbox
        self.mail_message_delivery_time = mail_message_delivery_time


class MitigationStatus(BaseModel):

    def __init__(self, raw_data, code, msg, batch_id, trace_id):
        super(MitigationStatus, self).__init__(raw_data)
        self.code = code
        self.msg = msg
        self.batch_id = batch_id
        self.trace_id = trace_id


class MitigationDetails(BaseModel):
    def __init__(self, raw_data, status, error_code, error_message, account_user_email):
        super(MitigationDetails, self).__init__(raw_data)
        self.status = status
        self.error_code = error_code
        self.error_message = error_message
        self.account_user_email = account_user_email
