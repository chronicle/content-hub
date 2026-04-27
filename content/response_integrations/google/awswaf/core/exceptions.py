from __future__ import annotations
class AWSWAFStatusCodeException(Exception):
    """
    Status Code exception from AWS WAF manager
    """

    pass


class AWSWAFValidationException(Exception):
    """
    Validation Exception for AWS WAF manager
    """

    pass


class AWSWAFCriticalValidationException(Exception):
    """
    Validation Exception for AWS WAF manager that should stop a playbook
    """

    pass


class AWSWAFNotFoundException(Exception):
    """
    Not Found Exception for AWS WAF manager
    """

    pass


class AWSWAFCriticalFNotFoundException(Exception):
    """
    Not Found Exception for AWS WAF manager that should stop a playbook
    """

    pass


class AWSWAFDuplicateItemException(Exception):
    """
    Duplicate Item Exception for AWS WAF Manager
    """

    pass


class AWSWAFLimitExceededException(Exception):
    """
    Resource Limit Exceeded for AWS WAF Manager
    """

    pass


class AWSWAFWebACLNotFoundException(Exception):
    """
    Web ACL Not Found Exception for AWS WAF
    """

    pass
