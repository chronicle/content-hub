from __future__ import annotations
from .datamodels import Finding, CustomDataIdentifier


class AmazonMacieParser:
    """
    Amazon Macie Transformation Layer.
    """

    @staticmethod
    def build_siemplify_finding_obj(raw_data):
        """
        :param raw_data: raw json response of single element in 'Findings' raw data response
        :return: Finding data model.
        """
        return Finding(
            raw_data,
            title=raw_data.get("title"),
            type=raw_data.get("type"),
            created_at=raw_data.get("createdAt"),
            updated_at=raw_data.get("updatedAt"),
            description=raw_data.get("description"),
            category=raw_data.get("category"),
            finding_id=raw_data.get("id"),
            account_id=raw_data.get("accountId"),
            archived=raw_data.get("archived"),
            severity=raw_data.get("severity", {}).get("description"),
            score=raw_data.get("severity", {}).get("score"),
            count=raw_data.get("count"),
        )

    @staticmethod
    def build_siemplify_data_identifier(raw_data):
        return CustomDataIdentifier(
            raw_data=raw_data, id=raw_data.get("customDataIdentifierId")
        )
