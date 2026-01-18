class SilentPushExceptions(Exception):
    """Custom Exception class for SilentPush Integration"""

    def __init__(self, message, **kwargs):
        super().__init__(message)
        self.details = kwargs