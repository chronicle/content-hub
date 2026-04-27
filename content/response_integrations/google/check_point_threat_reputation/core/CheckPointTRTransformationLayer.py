from __future__ import annotations
from .datamodels import ReputationClassification, ReputationContext

from .datamodels import IPReputationModel, FileHashReputationModel, HostReputationModel


class CheckPointTRTransformationLayer:

    @staticmethod
    def build_reputation_classification(raw_response_json):
        """
        :param raw_response_json: response api as json
        :return: ReputationClassification data model
        """
        raw_reputation_classification = raw_response_json[0].get("reputation", {})
        ## reputation classification
        return ReputationClassification(
            classification=raw_reputation_classification.get("classification"),
            severity=raw_reputation_classification.get("severity"),
            confidence=raw_reputation_classification.get("confidence"),
        )

    @staticmethod
    def build_reputation_context(raw_response_json):
        """
        :param raw_response_json: response api as json
        :return: ReputationClassification data model
        """
        raw_context = raw_response_json[0].get("context", {})
        ## retputation context
        return ReputationContext(
            raw_data=raw_context,
            asn=raw_context.get("asn"),
            as_owner=raw_context.get("as-owner"),
            safe=raw_context.get("safe"),
            malware_family=raw_context.get("malware_family"),
            protection_name=raw_context.get("protection_name"),
            redirections=raw_context.get("redirections"),
            malware_types=raw_context.get("malware_types"),  # list
            categories=raw_context.get("categories"),  # list of dictionaries
            indications=raw_context.get("indications"),
            location=raw_context.get("location"),  # dict
            vt_positives=raw_context.get("vt_positives"),
            alexa_rank=raw_context.get("alexa_rank"),
            creation_date=raw_context.get("creation_date"),
            meta_data=raw_context.get("metadata"),  # dict
        )

    @staticmethod
    def build_ip_response_reputation(raw_response_json):
        """
        :param raw_response_json: response api as json
        :return: IPReputationModel data model
        """
        return IPReputationModel(
            raw_data=raw_response_json[0],
            resource=raw_response_json[0].get("resource", ""),
            risk=raw_response_json[0].get("risk", 0),
            reputation_classification=CheckPointTRTransformationLayer.build_reputation_classification(
                raw_response_json
            ),
            reputation_context=CheckPointTRTransformationLayer.build_reputation_context(
                raw_response_json
            ),
        )

    @staticmethod
    def build_file_hash_response_reputation(raw_response_json):
        """
        :param raw_response_json: response api as json
        :return: FileHashReputationModel data model
        """
        return FileHashReputationModel(
            raw_data=raw_response_json[0],
            resource=raw_response_json[0].get("resource", ""),
            risk=raw_response_json[0].get("risk", 0),
            reputation_classification=CheckPointTRTransformationLayer.build_reputation_classification(
                raw_response_json
            ),
            reputation_context=CheckPointTRTransformationLayer.build_reputation_context(
                raw_response_json
            ),
        )

    @staticmethod
    def build_host_response_reputation(raw_response_json):
        """
        :param raw_response_json: response api as json
        :return: HostReputationModel data model
        """
        return HostReputationModel(
            raw_data=raw_response_json[0],
            resource=raw_response_json[0].get("resource", ""),
            risk=raw_response_json[0].get("risk", 0),
            reputation_classification=CheckPointTRTransformationLayer.build_reputation_classification(
                raw_response_json
            ),
            reputation_context=CheckPointTRTransformationLayer.build_reputation_context(
                raw_response_json
            ),
        )
