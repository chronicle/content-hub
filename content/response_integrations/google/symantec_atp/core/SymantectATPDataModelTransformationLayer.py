# description     :This Module contains the TransformationLayer from the raw data based on the datamodel
# author          :severins@siemplify.co
# date            :21-05-2020
# python_version  :2.7
# libraries       :
# requirements    :
# product_version :
# ============================================================================#


# ============================= IMPORTS ===================================== #

from __future__ import annotations
from .datamodels import Comment


class SymantecATPDataModelTransformationLayerError(Exception):
    """
    General Exception for SymantecATP DataModelTransformation
    """

    pass


def build_siemplify_comment_object(comment_json):
    return Comment(
        comment_json,
        comment=comment_json.get("comment"),
        time=comment_json.get("time"),
        incident_responder_name=comment_json.get("incident_responder_name"),
    )
