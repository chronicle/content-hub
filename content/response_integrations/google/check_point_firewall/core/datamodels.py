from __future__ import annotations
from .constants import LOG_MAPPING


class BaseModel:
    """
    Base model for inheritance
    """

    def __init__(self, raw_json):
        self.raw_data = raw_json

    def to_json(self):
        return self.raw_data


class AccessLayer(BaseModel):
    def __init__(
        self,
        raw_json,
        name,
        layer_type,
        shared,
        applications_and_url_filtering,
        content_awareness,
        mobile_access,
        firewall,
        comments,
        creator,
        read_only,
        uid,
    ):
        super(AccessLayer, self).__init__(raw_json)
        self.name = name
        self.type = layer_type
        self.shared = shared
        self.applications_and_url_filtering = applications_and_url_filtering
        self.content_awareness = content_awareness
        self.mobile_access = mobile_access
        self.firewall = firewall
        self.comments = comments
        self.creator = creator
        self.read_only = read_only
        self.uid = uid

    def to_csv(self):
        """
        Function that prepares the dict containing layer's data
        :return {dict} Dictionary containing Layer's data
        """
        return {
            "Name": self.name,
            "Type": self.type,
            "Shared": self.shared,
            "Application and URL Filtering": self.applications_and_url_filtering,
            "Content Awareness": self.content_awareness,
            "Mobile Access": self.mobile_access,
            "Firewall": self.firewall,
            "Comments": self.comments,
            "Creator": self.creator,
            "Read Only": self.read_only,
            "UID": self.uid,
        }


class ThreatLayer(BaseModel):
    def __init__(self, raw_json, name, ips_layer, comments, creator, read_only, uid):
        super(ThreatLayer, self).__init__(raw_json)
        self.name = name
        self.ips_layer = ips_layer
        self.comments = comments
        self.creator = creator
        self.read_only = read_only
        self.uid = uid

    def to_csv(self):
        """
        Function that prepares the dict containing layer's data
        :return {dict} Dictionary containing Layer's data
        """
        return {
            "Name": self.name,
            "IPS Layer": self.ips_layer,
            "Comments": self.comments,
            "Creator": self.creator,
            "Read Only": self.read_only,
            "UID": self.uid,
        }


class Policy(BaseModel):
    def __init__(self, raw_json):
        super(Policy, self).__init__(raw_json)


class LogResult(BaseModel):
    def __init__(self, raw_json, log_id, title, severity, subject, index_time, time):
        super(LogResult, self).__init__(raw_json)
        self.id = log_id
        self.title = title
        self.severity = severity
        self.subject = subject
        self.index_time = index_time
        self.time = time

    def __repr__(self):
        return f"{self.id}, {self.title}"

    def to_csv(self, log_type):
        """
        Function that prepares the dict containing only existing log results data
        :return {dict} Dictionary containing log results
        """
        data = {
            "ID": self.id,
            "Title": self.title,
            "Severity": self.severity,
            "Subject": self.subject,
        }
        # Add properties by Log Type only for 2 cases handled
        if log_type == LOG_MAPPING["Log"]:
            data["Index Time"] = self.index_time
        else:
            data["Time"] = self.time

        return data


class Task(BaseModel):
    def __init__(self, raw_json, log_id, attachments):
        super(Task, self).__init__(raw_json)
        self.task_id = raw_json.get("task-id")
        self.log_id = log_id
        self.attachments = attachments

    def filter_attachments_by_size(self, min_mb=0, max_mb=3):
        """
        Filter and get attachments by size specified in arguments
        :param max_mb: {int} more than
        :param min_mb: {int} less than
        """
        return list(
            filter(
                lambda attachment: min_mb < attachment.size < max_mb, self.attachments
            )
        )


class Attachment(BaseModel):
    def __init__(self, raw_json, content, filename):
        super(Attachment, self).__init__(raw_json)
        self.content = content
        self.filename = filename

    @property
    def size(self):
        size_in_mb = ((len(self.content) * 3) / 4 - self.content.count("=", -2)) / (
            1024 * 1024
        )

        return round(size_in_mb, 2)
