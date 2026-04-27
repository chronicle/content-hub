from __future__ import annotations
from TIPCommon import dict_to_flat, add_prefix_to_dict

RED_COLOR = "#ff0000"
BLACK_COLOR = "#000000"


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


class Submission(BaseModel):
    def __init__(self, raw_data, id, status, result_id):
        super(Submission, self).__init__(raw_data)
        self.id = id
        self.status = status
        self.result_id = result_id


class SubmissionResult(BaseModel):
    def __init__(
        self,
        raw_data,
        malicious,
        severity,
        process,
        cnc_service,
        regkey,
        file_extracted,
    ):
        super(SubmissionResult, self).__init__(raw_data)
        self.malicious = malicious
        self.severity = severity
        self.cnc_service = cnc_service
        self.process = process
        self.regkey = regkey
        self.file_extracted = file_extracted

    def to_enrichment_data(self, prefix=None):
        data = dict_to_flat({"malicious": self.malicious, "severity": self.severity})
        return add_prefix_to_dict(data, prefix) if prefix else data

    def to_insight(self):
        if self.malicious:
            malicious_color = RED_COLOR
            malicious_text = f'<h2><strong>Malicious: </strong><span style="color: {malicious_color};">{self.malicious}</span></h2>'
        else:
            malicious_text = f"<h2><strong>Malicious: </strong>{self.malicious}</h2>"
        return (
            f"<br><p>"
            f"{malicious_text}"
            f"<strong><br />Severity: </strong>{self.severity}"
            f"<strong><br />C&C Services Count: </strong>{len(self.cnc_service)}<br />"
            f"<strong>Executed Processes Count: </strong>{len(self.process)}<br />"
            f"<strong>Registry Changes Count: </strong>{len(self.regkey)}<br/>"
            f"<strong>Extracted Files Count: </strong>{len(self.file_extracted)}"
            f"</p>"
        )

    def to_file_json(self, file_path):
        self.raw_data["absolute_path"] = file_path
        return self.raw_data

    def to_table(self):
        return {"malicious": self.malicious, "severity": self.severity}
