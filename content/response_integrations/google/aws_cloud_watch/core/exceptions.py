from __future__ import annotations
class AWSCloudWatchStatusCodeException(Exception):
    """
    Status Code exception from AWS CloudWatch manager
    """

    pass


class AWSCloudWatchInvalidParameterException(Exception):
    """
    Invalid Parameter exception from AWS CloudWatch manager
    """

    pass


class AWSCloudWatchValidationException(Exception):
    """
    Validation exception from AWS CloudWatch manager
    """

    pass


class AWSCloudWatchResourceNotFoundException(Exception):
    """
    Resource Not Found exception from AWS CloudWatch manager
    """

    pass


class AWSCloudWatchLogGroupNotFoundException(Exception):
    """
    Log Group Not Found exception from AWS CloudWatch manager
    """

    pass


class AWSCloudWatchLogStreamNotFoundException(Exception):
    """
    Log Stream Not Found exception from AWS CloudWatch manager
    """

    pass
