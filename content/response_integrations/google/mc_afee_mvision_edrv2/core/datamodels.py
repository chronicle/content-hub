from __future__ import annotations
class BaseModel:
    """
    Base model for inheritance
    """

    def __init__(self, raw_data):
        self.raw_data = raw_data

    def to_json(self):
        return self.raw_data


class Investigation(BaseModel):
    def __init__(
        self,
        raw_data,
        name,
        owner,
        created,
        investigation_id,
        summary,
        last_modified,
        is_automatic,
        hint,
        case_type,
        investigated,
        status,
        priority,
    ):
        super(Investigation, self).__init__(raw_data)
        self.name = name
        self.owner = owner
        self.created = created
        self.investigation_id = investigation_id
        self.summary = summary
        self.last_modified = last_modified
        self.is_automatic = is_automatic
        self.hint = hint
        self.case_type = case_type
        self.investigated = investigated
        self.status = status
        self.priority = priority

    def to_table_data(self):
        return {
            "ID": self.investigation_id,
            "Name": self.name,
            "Created At": self.created,
            "Last Modified": self.last_modified,
            "Owner": self.owner,
            "Summary": self.summary,
            "Is Automatic": self.is_automatic,
            "Hint": self.hint,
            "Case Type": self.case_type,
            "Investigated": self.investigated,
            "Status": self.status,
            "Priority": self.priority,
        }
