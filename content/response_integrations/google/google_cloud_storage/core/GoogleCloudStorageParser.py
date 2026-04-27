from __future__ import annotations
from .datamodels import Bucket, ACL, BucketObject


class GoogleCloudStorageParser:
    """
    Google Cloud Storage Transformation Layer.
    """

    @staticmethod
    def build_buckets_obj(raw_data):
        raw_data_buckets = raw_data.get("items", [])
        return [
            GoogleCloudStorageParser.build_bucket_obj(raw_data_bucket)
            for raw_data_bucket in raw_data_buckets
        ]

    @staticmethod
    def build_bucket_obj(raw_data):
        return Bucket(
            raw_data=raw_data,
            creation_date=raw_data.get("timeCreated", ""),
            modification_date=raw_data.get("updated", ""),
            name_value=raw_data.get("name", ""),
            owner_value=raw_data.get("owner", ""),
            **raw_data
        )

    @staticmethod
    def build_bucket_from_google_obj(bucket_object):
        return Bucket(
            raw_data=None,
            bucket_data=bucket_object,
            creation_date=bucket_object.time_created,
            name_value=bucket_object.name,
            owner_value=bucket_object.owner,
        )

    @staticmethod
    def build_bucket_object_obj(blob, retrieve_acl=True):
        bucket = ""
        if blob.bucket:
            bucket = blob.bucket.name if blob.bucket.name else ""

        name = blob.name if blob.name else ""
        content_type = blob.content_type if blob.content_type else ""
        time_created = blob.time_created if blob.time_created else ""
        time_updated = blob.updated if blob.updated else ""
        md5 = blob.md5_hash if blob.md5_hash else ""
        owner = blob.owner if blob.owner else ""
        crc32c = blob.crc32c if blob.crc32c else ""
        id = blob.id if blob.id else ""
        size = blob.size if blob.size else ""

        if retrieve_acl:
            acl = GoogleCloudStorageParser.build_bucket_object_acl_obj(blob.acl)
        else:
            acl = None

        return BucketObject(
            object_data=blob,
            bucket=bucket,
            object_name=name,
            content_type=content_type,
            time_created=time_created,
            time_updated=time_updated,
            md5=md5,
            owner=owner,
            crc32c=crc32c,
            id=id,
            size=size,
            acl=acl,
        )

    @staticmethod
    def build_acl_obj(bucket):
        acl = bucket.acl
        entries = []
        for entry in acl:
            # Uniform bucket will raise an error when trying to retrieve an entity/role from an ACL
            entries.append({"Entity": entry.get("entity"), "Role": entry.get("role")})

        return ACL(acl_data=acl, entries=entries)

    @staticmethod
    def build_bucket_object_acl_obj(acl):
        entries = []
        for entry in acl:
            # Uniform bucket will raise an error when trying to retrieve an entity/role from an ACL
            entries.append({"Entity": entry.get("entity"), "Role": entry.get("role")})

        return ACL(acl_data=acl, entries=entries)
