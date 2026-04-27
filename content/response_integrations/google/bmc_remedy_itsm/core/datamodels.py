from __future__ import annotations
from TIPCommon.transformation import dict_to_flat, add_prefix_to_dict
import copy


class BaseModel:
    """
    Base model for inheritance
    """

    def __init__(self, raw_data):
        self.raw_data = raw_data

    def to_json(self):
        return self.raw_data

    def to_table(self):
        return dict_to_flat(self.to_json())

    def to_enrichment_data(self, prefix=None):
        data = dict_to_flat(self.raw_data)
        return add_prefix_to_dict(data, prefix) if prefix else data


class Template(BaseModel):
    def __init__(self, raw_data, template_id):
        super(Template, self).__init__(raw_data)
        self.template_id = template_id


class Incident(BaseModel):
    def __init__(self, raw_data, request_id, entry_id, status):
        super(Incident, self).__init__(raw_data)
        self.request_id = request_id
        self.entry_id = entry_id
        self.status = status


class IncidentDetails(BaseModel):
    def __init__(self, raw_data, inc_number):
        super(IncidentDetails, self).__init__(raw_data)
        self.incident_number = inc_number
        self.worknotes = []

    def to_json(self):
        json_data = copy.deepcopy(self.raw_data)
        if self.worknotes:
            json_data["Worknotes"] = [worknote.to_json() for worknote in self.worknotes]
        return json_data

    def to_table(self):
        return dict_to_flat(self.raw_data)


class WorkNote(BaseModel):
    def __init__(self, raw_data, submitter, description, submit_date):
        super(WorkNote, self).__init__(raw_data)
        self.submitter = submitter
        self.description = description
        self.submit_date = submit_date

    def to_table(self):
        return dict_to_flat(
            {
                "Submitter": self.submitter,
                "Text": self.description,
                "Time": self.submit_date,
            }
        )


class RecordDetails(BaseModel):
    def __init__(self, raw_data):
        super(RecordDetails, self).__init__(raw_data)


class Record(BaseModel):
    def __init__(
        self,
        raw_data,
        work_log_id=None,
        submitter=None,
        submit_date=None,
        assigned_to=None,
        last_modified_by=None,
        last_modified_date=None,
        status=None,
        short_description=None,
        status_history=None,
        assignee_groups=None,
    ):
        super().__init__(raw_data)
        self.work_log_id = work_log_id
        self.submitter = submitter
        self.submit_date = submit_date
        self.assigned_to = assigned_to
        self.last_modified_by = last_modified_by
        self.last_modified_date = last_modified_date
        self.status = status
        self.short_description = short_description
        self.status_history = status_history
        self.assignee_groups = assignee_groups

    def to_json(self):
        return {
            "Work Log ID": self.work_log_id,
            "Submitter": self.submitter,
            "Submit Date": self.submit_date,
            "Assigned To": self.assigned_to,
            "Last Modified By": self.last_modified_by,
            "Last Modified Date": self.last_modified_date,
            "Status": self.status,
            "Short Description": self.short_description,
            "Status History": self.status_history,
            "Assignee Groups": self.assignee_groups,
        }
