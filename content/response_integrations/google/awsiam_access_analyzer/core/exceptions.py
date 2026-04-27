from __future__ import annotations
class AWSIAMStatusCodeException(Exception):
    """
    Status Code exception for IAM Access Analyzer
    """

    pass


class AWSIAMValidationException(Exception):
    """
    Validation Exception for IAM Access Analyzer
    """

    pass


class AWSIAMCriticalValidationException(Exception):
    """
    Validation Exception for IAM Access Analyzer
    """

    pass


class AWSIAMNotFoundException(Exception):
    """
    Not Found Exception for IAM Access Analyzer
    """

    pass


class AWSIAMAnalyzerNotFoundException(Exception):
    """
    Analyzer Not Found Exception for IAM Access Analyzer
    """

    pass
