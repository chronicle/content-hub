from __future__ import annotations
class Bucket:
    """
    Google Cloud Storage Bucket
    """

    def __init__(
        self,
        raw_data,
        bucket_data=None,
        creation_date=None,
        modification_date=None,
        name_value=None,
        owner_value=None,
        **kwargs
    ):
        self.raw_data = raw_data
        self.bucket_data = bucket_data
        self.creation_date = creation_date
        self.modification_date = modification_date
        self.name = name_value
        self.owner = owner_value

    def as_json(self):
        return {
            "CreationDate": self.creation_date,
            "ModificationDate": self.modification_date,
            "Name": self.name,
            "Owner": self.owner,
        }


class BucketObject:
    """
    Google Cloud Storage Bucket Object
    """

    def __init__(
        self,
        object_data=None,
        bucket=None,
        object_name=None,
        content_type=None,
        time_created=None,
        time_updated=None,
        md5=None,
        owner=None,
        crc32c=None,
        id=None,
        acl=None,
        size=None,
    ):
        self.bucket = bucket
        self.object_data = object_data
        self.object_name = object_name
        self.content_type = content_type
        self.time_created = time_created
        self.time_updated = time_updated
        self.md5 = md5
        self.owner = owner
        self.crc32c = crc32c
        self.id = id
        self.acl = acl
        self.size = size

    def as_json(self):
        payload = {
            "ObjectName": self.object_name,
            "Bucket": self.bucket,
            "ContentType": self.content_type,
            "TimeCreated": self.time_created,
            "TimeUpdated": self.time_updated,
            "Size": self.size,
            "MD5": self.md5,
            "Owner": self.owner,
            "CR32c": self.crc32c,
            "id": self.id,
        }

        if self.acl:
            payload["ObjectACL"] = self.acl.as_json()

        return payload


class ACL:
    """
    Google Cloud Storage ACL
    """

    def __init__(self, acl_data=None, entries=None):
        self.acl_data = acl_data
        self.entries = entries

    def as_json(self):
        return self.entries


class Blob:
    """
    Google Cloud Storage Blob
    """

    def __init__(self, id=None, name=None, md5_hash=None, object_path=None):
        self.id = id
        self.name = name
        self.md5_hash = md5_hash
        self.object_path = object_path

    def as_json(self):
        return {
            "object_id": self.id,
            "Object_name": self.name,
            "md5_hash": self.md5_hash,
            "object_path": self.object_path,
        }


class DownloadedBlob:
    """
    Downloaded Blob data model
    """

    def __init__(self, object_name, download_path):
        self.object_name = object_name
        self.download_path = download_path

    def as_json(self):
        return {"object_name": self.object_name, "download_path": self.download_path}
