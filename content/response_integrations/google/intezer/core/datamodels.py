from __future__ import annotations
from TIPCommon.data_models import BaseDataModel


class Detonate(BaseDataModel):
    """Defines the structure for a Detonate URL"""

    def __init__(
        self,
        raw_data: dict,
        analysis_id: str,
        analysis_status: str,
        analysis_type: str,
        identifier: str,
    ):
        super().__init__(raw_data)
        self.analysis_id = analysis_id
        self.analysis_status = analysis_status
        self.analysis_type = analysis_type
        self.identifier = identifier


class Alert(BaseDataModel):
    """Defines the structure for an Alert"""

    def __init__(self, raw_data: dict, status: str):
        super().__init__(raw_data)
        self.status = status


class SubmitAlert(BaseDataModel):
    """Defines the structure for a Submit Alert"""

    def __init__(self, raw_data: dict, alert_id: str):
        super().__init__(raw_data)
        self.alert_id = alert_id


class URLReport(BaseDataModel):
    """Defines the structure for a UrlReport URL"""

    def __init__(self, result_data: dict, status: str):
        super().__init__(result_data)
        self.status = status


class Id:
    """Defines the structure for an Id"""

    def __init__(self, item_id: str) -> None:
        self.id = item_id


class IndexFile(BaseDataModel):
    """Defines the structure for an Index File"""

    def __init__(self, result_data: dict, status: str):
        super().__init__(result_data)
        self.status = status


class SubmitEmail(BaseDataModel):
    """Defines the structure for SubmitEmail"""

    def __init__(self, raw_data: dict, alert_id: str):
        super().__init__(raw_data)
        self.alert_id = alert_id


class FileAnalysis:
    """Defines the structure for a File Report Analysis"""

    def __init__(self, status: str, analysis: dict):
        self.analysis = analysis
        self.status = status


class FileAnalysisResult(BaseDataModel):
    """Defines the structure for a FileAnalysisResult"""

    def __init__(self, result_data: dict, analysis_id: str, status: str):
        super().__init__(result_data)
        self.analysis_id = analysis_id
        self.status = status


class Ioc(BaseDataModel):
    """Defines the structure for an Ioc details related to a file analysis"""


class Ttps(BaseDataModel):
    """Defines the structure for dynamic-ttps details related to a file analysis"""


class SubAnalysis:
    """Defines a sub analysis id for sub analyses of a file"""

    def __init__(self, sub_analysis_id: str):
        self.sub_analysis_id = sub_analysis_id


class SubAnalysisMetaData(BaseDataModel):
    """Defines the structure for a sub analysis metadata"""


class SubAnalysisCodeReuse(BaseDataModel):
    """Defines the structure for a sub analysis code reuse"""
