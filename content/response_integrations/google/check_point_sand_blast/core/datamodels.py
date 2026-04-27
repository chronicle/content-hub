from __future__ import annotations
from TIPCommon import add_prefix_to_dict
from enum import IntEnum
from . import consts


class Features:
    THREAT_EMULATION = "te"
    ANTI_VIRUS = "av"
    THREAT_EXTRACTION = "extraction"


class HashTypes:
    MD5 = "md5"
    SHA1 = "sha1"
    SHA256 = "sha256"


class StatusCodes(IntEnum):
    FOUND = 1001
    UPLOAD_SUCCESS = 1002
    PENDING = 1003
    NOT_FOUND = 1004
    NO_QUOTA = 1005
    PARTIALLY_FOUND = 1006
    FILE_TYPE_NOT_SUPPORTED = 1007
    BAD_REQUEST = 1008
    INTERNAL_ERROR = 1009
    FORBIDDEN = 1010
    NOT_ENOUGH_RESOURCES = 1011


class Status:
    def __init__(self, raw_data, code=None, label=None, message=None, **kwargs):
        self.raw_data = raw_data
        self.code = code
        self.label = label
        self.message = message


class TEResponse:
    class Image:
        def __init__(
            self,
            status=None,
            id=None,
            revision=None,
            verdict=None,
            xml_report=None,
            tar_report=None,
            **kwargs
        ):
            self.status = status
            self.id = id
            self.revision = revision
            self.verdict = verdict
            self.xml_report = xml_report
            self.tar_report = tar_report

    def __init__(
        self,
        raw_data,
        combined_verdict=None,
        severity=None,
        status=None,
        confidence=None,
        summary_report=None,
        images=None,
        **kwargs
    ):
        self.raw_data = raw_data
        self.combined_verdict = combined_verdict
        self.severity = severity
        self.status = status
        self.confidence = confidence
        self.summary_report = summary_report
        self.images = images

    def as_enrichment(self):
        return add_prefix_to_dict(
            {
                "te_combined_verdict": self.combined_verdict,
                "te_severity": self.severity,
                "te_confidence": self.confidence,
            },
            consts.PREFIX,
        )


class AVResponse:
    class MalwareInfo:
        def __init__(
            self,
            signature_name=None,
            malware_family=None,
            malware_type=None,
            severity=None,
            confidence=None,
            **kwargs
        ):
            self.signature_name = signature_name
            self.malware_family = malware_family
            self.malware_type = malware_type
            self.severity = severity
            self.confidence = confidence

    def __init__(self, raw_data, malware_info=None, status=None, **kwargs):
        self.raw_data = raw_data
        self.malware_info = (
            AVResponse.MalwareInfo(**malware_info) if malware_info else None
        )
        self.status = status

    def as_enrichment(self):
        return add_prefix_to_dict(
            {
                "av_signature_name": self.malware_info.signature_name,
                "av_severity": self.malware_info.severity,
                "av_confidence": self.malware_info.confidence,
            },
            consts.PREFIX,
        )


class ExtractionResponse:
    class ExtractionData:
        def __init__(
            self,
            input_extension=None,
            input_real_extension=None,
            orig_file_url=None,
            output_file_name=None,
            risk=None,
            scrub_method=None,
            protection_type=None,
            protection_name=None,
            scrub_result=None,
            message=None,
            scrub_activity=None,
            scrub_time=None,
            scrubbed_content=None,
            **kwargs
        ):
            self.input_extension = input_extension
            self.input_real_extension = input_real_extension
            self.orig_file_url = orig_file_url
            self.output_file_name = output_file_name
            self.risk = risk
            self.scrub_method = scrub_method
            self.protection_type = protection_type
            self.protection_name = protection_name
            self.scrub_result = scrub_result
            self.message = message
            self.scrub_activity = scrub_activity
            self.scrub_time = scrub_time
            self.scrubbed_content = scrubbed_content

    def __init__(
        self,
        raw_data,
        tex_product=None,
        extract_result=None,
        extracted_file_download_id=None,
        extraction_data=None,
        status=None,
        **kwargs
    ):
        self.raw_data = raw_data
        self.tex_product = tex_product
        self.extract_result = extract_result
        self.extracted_file_download_id = extracted_file_download_id
        self.extraction_data = (
            ExtractionResponse.ExtractionData(**extraction_data)
            if extraction_data
            else None
        )
        self.status = status


class QueryResponse:
    def __init__(
        self,
        raw_data,
        md5=None,
        sha1=None,
        sha256=None,
        file_name=None,
        features=None,
        file_type=None,
        status=None,
        te_response=None,
        av_response=None,
        extraction_response=None,
        **kwargs
    ):
        self.raw_data = raw_data
        self.md5 = md5
        self.sha1 = sha1
        self.sha256 = sha256
        self.file_name = file_name
        self.file_type = file_type
        self.features = features
        self.status = status
        self.te_response = te_response
        self.av_response = av_response
        self.extraction_response = extraction_response
