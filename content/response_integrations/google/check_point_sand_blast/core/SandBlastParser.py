from __future__ import annotations
from .datamodels import QueryResponse, Status, TEResponse, AVResponse, ExtractionResponse
from copy import deepcopy


class SandBlastParser:
    """
    SandBlast Transformation Layer.
    """

    @staticmethod
    def build_siemplify_query_response_obj(query_data):
        raw_data = deepcopy(query_data)
        status = SandBlastParser.build_siemplify_status_obj(
            query_data.pop("status", {})
        )

        if "te" in query_data:
            te_response = SandBlastParser.build_siemplify_te_response_obj(
                query_data["te"]
            )
        else:
            te_response = None

        if "av" in query_data:
            av_response = SandBlastParser.build_siemplify_av_response_obj(
                query_data["av"]
            )
        else:
            av_response = None

        if "extraction" in query_data:
            extraction_response = (
                SandBlastParser.build_siemplify_extraction_response_obj(
                    query_data["extraction"]
                )
            )
        else:
            extraction_response = None

        return QueryResponse(
            raw_data=raw_data,
            te_response=te_response,
            av_response=av_response,
            extraction_response=extraction_response,
            status=status,
            **query_data
        )

    @staticmethod
    def build_siemplify_status_obj(status_data):
        return Status(raw_data=status_data, **status_data)

    @staticmethod
    def build_siemplify_image_obj(image_data):
        return TEResponse.Image(
            status=image_data.get("status"),
            id=image_data.get("id"),
            revision=image_data.get("revision"),
            verdict=image_data.get("report", {}).get("verdict"),
            xml_report=image_data.get("report", {}).get("xml_report"),
            tar_report=image_data.get("report", {}).get("tar_report"),
        )

    @staticmethod
    def build_siemplify_te_response_obj(te_data):
        raw_data = deepcopy(te_data)
        status = SandBlastParser.build_siemplify_status_obj(te_data.pop("status", {}))
        images = [
            SandBlastParser.build_siemplify_image_obj(image)
            for image in te_data.pop("images", [])
        ]
        return TEResponse(raw_data=raw_data, status=status, images=images, **te_data)

    @staticmethod
    def build_siemplify_av_response_obj(av_data):
        raw_data = deepcopy(av_data)
        status = SandBlastParser.build_siemplify_status_obj(av_data.pop("status", {}))
        return AVResponse(raw_data=raw_data, status=status, **av_data)

    @staticmethod
    def build_siemplify_extraction_response_obj(extraction_data):
        raw_data = deepcopy(extraction_data)
        status = SandBlastParser.build_siemplify_status_obj(
            extraction_data.pop("status", {})
        )
        return ExtractionResponse(raw_data=raw_data, status=status, **extraction_data)
