from __future__ import annotations
from .datamodels import Process, FileHashMetadata, FileHashSummary, Event


class CBEnterpriseEDRParser:
    """
    CB Enterprise EDR Transformation Layer.
    """

    @staticmethod
    def build_siemplify_process_obj(process_data):
        return Process(raw_data=process_data, **process_data)

    @staticmethod
    def build_siemplify_event_obj(event_data):
        return Event(raw_data=event_data, **event_data)

    @staticmethod
    def build_siemplify_filehash_metadata_obj(filehash_metadata):
        return FileHashMetadata(raw_data=filehash_metadata, **filehash_metadata)

    @staticmethod
    def build_siemplify_filehash_summary_obj(filehash_summary):
        return FileHashSummary(raw_data=filehash_summary, **filehash_summary)
