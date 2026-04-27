from __future__ import annotations
class AWSGuardDutyStatusCodeException(Exception):
    """
    Status Code exception from AWS GuardDuty manager
    """

    pass


class AWSGuardDutyValidationException(Exception):
    """
    Validation Exception for AWS GuardDuty manager
    """

    pass


class AWSGuardDutyResourceAlreadyExistsException(Exception):
    """
    Resource already exists Exception for AWS GuardDuty manager
    """

    pass


class AWSGuardDutyNotFoundException(Exception):
    """
    Not Found Exception for AWS GuardDuty manager
    """

    pass
