from __future__ import annotations
class GoogleCloudRecommenderError(Exception):
    """
    General Exception for Google Cloud Recommender
    """

    pass


class GoogleCloudRecommenderInvalidJsonError(Exception):
    """
    Exception in case of Invalid JSON
    """

    pass


class GoogleCloudRecommenderStateNoChangeError(Exception):
    """
    Exception in case of State not changed
    """

    pass


class GoogleCloudRecommenderStatusNotFoundError(GoogleCloudRecommenderError):
    """
    Exception in case of requested response not found.
    """

    pass


class GoogleCloudRecommenderValidationError(GoogleCloudRecommenderError):
    """
    Exception in case of invalid data provided.
    """

    pass


class GoogleCloudRecommenderPermissionsDeniedError(GoogleCloudRecommenderError):
    """
    Exception in case of permissions denied on your request.
    """

    pass
