# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

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
