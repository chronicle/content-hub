from __future__ import annotations
from datetime import datetime

from .consts import DATE_FORMAT


class Bucket:
    """
    AWS S3 Bucket data model.
    """

    def __init__(self, name=None, creation_date=None):
        self.name = name
        self.creation_date = datetime.strftime(creation_date, DATE_FORMAT)

    def to_dict(self):
        """
        :return: {dict} of Bucket data model.
        """
        return {"CreationDate": self.creation_date, "Name": self.name}


class Owner:
    """
    AWS S3 Bucket Owner data model.
    """

    def __init__(self, display_name=None, id=None):
        self.display_name = display_name
        self.id = id

    def to_dict(self):
        """
        :return: {dict} of Bucket Owner data model.
        """
        return {"DisplayName": self.display_name, "ID": self.id}


class BucketPolicy:
    """
    AWS S3 Bucket Policy data model.
    """

    class Statement:
        """
        Bucket Policy Statement data model.
        """

        def __init__(
            self, sid=None, effect=None, principal=None, action=None, resource=None
        ):
            self.sid = sid
            self.effect = effect
            self.principal = principal
            self.action = action
            self.resource = resource

        def to_dict(self):
            """
            :return: {dict} of Bucket Policy Statement data model.
            """
            return {
                "Sid": self.sid,
                "Effect": self.effect,
                "Principal": self.principal,
                "Action": self.action,
                "Resource": self.resource,
            }

    def __init__(self, version=None, statements=None):
        """
        :param version: {str} Bucket policy version
        :param statements: list of Statement data models
        """
        self.version = version
        self.statements = statements

    def to_dict(self):
        """
        :return: {dict} of Bucket Policy data model.
        """
        return {
            "Version": self.version,
            "Statement": [statement.to_dict() for statement in self.statements],
        }


class BucketContent:
    """
    AWS S3 Bucket Content object data model.
    """

    def __init__(
        self,
        key=None,
        last_modified=None,
        etag=None,
        size=None,
        storage_class=None,
        owner=None,
    ):
        self.key = key
        self.last_modified = datetime.strftime(last_modified, DATE_FORMAT)
        self.etag = etag
        self.size = size
        self.storage_class = storage_class
        self.owner = owner

    def to_dict(self):
        """
        :return: {dict} of Bucket Content data model.
        """
        return {
            "Key": self.key,
            "LastModified": self.last_modified,
            "ETag": self.etag,
            "Size": self.size,
            "StorageClass": self.storage_class,
            "Owner": self.owner.to_dict(),
        }

    def to_csv(self):
        """
        :return: {dict} csv table of Bucket Content data model
        """
        return {
            "Key": self.key,
            "LastModified": self.last_modified,
            "Size (Bytes)": self.size,
            "Owner": self.owner.display_name,
            "Storage Class": self.storage_class,
        }
