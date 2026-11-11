from __future__ import annotations

from typing import Callable
import collections
import time

from soar_sdk.SiemplifyLogger import SiemplifyLogger
from google_cloud_armor.core import constants
from google_cloud_armor.core.datamodels import ListSecurityPolicy
from google_cloud_armor.core import exceptions


SecurityPolicyData = collections.namedtuple(
    "SecurityPolicyData", ["policy_name", "region"]
)


def get_security_policy(
    get_policy: Callable[[str, str], ListSecurityPolicy],
    logger: SiemplifyLogger,
    policy_data: SecurityPolicyData,
    retries: int = constants.DEFAULT_RETRIES,
) -> ListSecurityPolicy:
    """Get the created or updated security policy.

    This function retrieves the created or updated security policy until timeout.

    Args:
        manager (ApiManager): The ApiManager instance.
        region (str): The region of the security policy.
        security_policy (str): The name of the security policy.
        retries (int): The number of retries.

    Raises:
        TimeoutReachedException: Raised if the timeout is reached while searching for
            the security policy.

    Returns:
        ListSecurityPolicy: The retrieved security policy datamodel.ListSecurityPolicy.
    """
    for _ in range(retries + 1):
        time.sleep(constants.TIME_INTERVAL)
        logger.info(f'Getting security policy "{policy_data.policy_name}".')
        try:
            return get_policy(
                region=policy_data.region, security_policy=policy_data.policy_name
            )

        except exceptions.GoogleCloudArmorStatusNotFoundError as e:
            logger.error(e)
            logger.info("Retrying...!")

    raise exceptions.GoogleCloudArmorRetryExceededError(
        f'Failed to create security policy "{policy_data.policy_name}".'
    )
