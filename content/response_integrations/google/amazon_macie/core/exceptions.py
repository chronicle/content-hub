from __future__ import annotations
class AmazonMacieStatusCodeException(Exception):
    """
    Status Code exception from Amazon Macie manager
    """

    pass


class AmazonMacieValidationException(Exception):
    """
    Validation Exception for Amazon Macie manager
    """

    pass


class AmazonMacieResourceAlreadyExistsException(Exception):
    """
    Resource already exists Exception for Amazon Macie manager
    """

    pass


class AmazonMacieNotFoundException(Exception):
    """
    Not Found Exception for Amazon Macie manager
    """

    pass
