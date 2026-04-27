from __future__ import annotations
class AWSSecurityHubStatusCodeException(Exception):
    """
    Status Code exception from AWS Security Hub manager
    """

    pass


class AWSSecurityHubValidationException(Exception):
    """
    Validation Exception for AWS Security Hub manager
    """

    pass


class AWSSecurityHubCriticalValidationException(Exception):
    """
    Validation Exception for AWS Security Hub manager that should stop a playbook
    """

    pass


class AWSSecurityHubNotFoundException(Exception):
    """
    Not Found Exception for AWS Security Hub manager
    """

    pass
