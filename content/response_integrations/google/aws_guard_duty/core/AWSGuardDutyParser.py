from __future__ import annotations
from .datamodels import Finding, IpSet, TISet, Detector


class AWSGuardDutyParser:
    """
    AWS Guard Duty Transformation Layer.
    """

    @staticmethod
    def build_siemplify_finding_obj(raw_data, detector_id: str):
        """
        :param raw_data: raw json response of single element in 'Findings' raw data response
        :param detector_id: detector_id using which the data was retireved
        :return: Finding data model.
        """
        return Finding(
            raw_data,
            detector_id=detector_id,
            title=raw_data.get("Title"),
            type=raw_data.get("Type"),
            resource_id=raw_data.get("Resource", {})
            .get("InstanceDetails", {})
            .get("InstanceId"),
            created_at=raw_data.get("CreatedAt"),
            updated_at=raw_data.get("UpdatedAt"),
            description=raw_data.get("Description"),
            finding_id=raw_data.get("Id"),
            account_id=raw_data.get("AccountId"),
            arn=raw_data.get("Arn"),
            severity=raw_data.get("Severity"),
            confidence=raw_data.get("Confidence"),
            count=raw_data.get("Service", {}).get("Count"),
        )

    @staticmethod
    def build_siemplify_ip_set_obj(raw_data, id=None):
        """
        :param raw_data: raw json response of single element in 'IpSet' raw data response
        :return: IpSet data model.
        """
        return IpSet(
            raw_data,
            id=id,
            name=raw_data.get("Name"),
            format=raw_data.get("Format"),
            location=raw_data.get("Location"),
            status=raw_data.get("Status"),
            tags=raw_data.get("Tags", []),
        )

    @staticmethod
    def build_siemplify_threat_intel_set_obj(raw_data, id=None):
        """
        :param raw_data: raw json response of single element in 'threatIntelSet' raw data response
        :return: TISet data model.
        """
        return TISet(
            raw_data,
            id=id,
            name=raw_data.get("Name"),
            format=raw_data.get("Format"),
            location=raw_data.get("Location"),
            status=raw_data.get("Status"),
            tags=raw_data.get("Tags", []),
        )

    @staticmethod
    def build_siemplify_detector_obj(raw_data, id=None):
        """
        :param raw_data: raw json response of single element in 'threatIntelSet' raw data response
        :return: TISet data model.
        """
        return Detector(
            raw_data,
            id=id,
            created_at=raw_data.get("CreatedAt"),
            updated_at=raw_data.get("UpdatedAt"),
            service_role=raw_data.get("ServiceRole"),
            status=raw_data.get("Status"),
            finding_publishing_frequency=raw_data.get("FindingPublishingFrequency"),
            tags=raw_data.get("Tags", []),
        )
