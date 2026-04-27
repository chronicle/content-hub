from __future__ import annotations
from .datamodels import Owner, Bucket, BucketPolicy, BucketContent


class AWSS3Parser:
    """
    AWS S3 Transformation Layer.
    """

    @staticmethod
    def build_owner(owner):
        return Owner(display_name=owner.get("DisplayName"), id=owner.get("ID"))

    @staticmethod
    def build_bucket(bucket):
        return Bucket(name=bucket.get("Name"), creation_date=bucket.get("CreationDate"))

    @staticmethod
    def build_bucket_policy(bucket_policy):
        statements = bucket_policy.get("Statement")
        statements_dm = []  # list of statement data models
        if statements:
            for statement in statements:
                statements_dm.append(
                    BucketPolicy.Statement(
                        sid=statement.get("Sid"),
                        effect=statement.get("Effect"),
                        principal=statement.get("Principal"),
                        action=statement.get("Action"),
                        resource=statement.get("Resource"),
                    )
                )
        return BucketPolicy(
            version=bucket_policy.get("Version"), statements=statements_dm
        )

    @staticmethod
    def build_bucket_content(bucket_content):
        owner = bucket_content.get("Owner")

        if owner:
            owner_datamodel = Owner(
                display_name=owner.get("DisplayName"), id=owner.get("ID")
            )
        else:
            owner_datamodel = Owner()

        return BucketContent(
            key=bucket_content.get("Key"),
            last_modified=bucket_content.get("LastModified"),
            etag=bucket_content.get("ETag"),
            size=bucket_content.get("Size"),
            storage_class=bucket_content.get("StorageClass"),
            owner=owner_datamodel,
        )
