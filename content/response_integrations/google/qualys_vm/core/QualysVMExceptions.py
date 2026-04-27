from __future__ import annotations
class QualysVMManagerError(Exception):
    """
    General Exception for QualysVM manager
    """

    pass


class ScanErrorException(Exception):
    """
    Exception in case of scan error
    """

    pass


class QualysReportFailed(Exception):
    """
    Exception in case a report wasn't found
    """

    pass
