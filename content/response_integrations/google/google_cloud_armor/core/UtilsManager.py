# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import annotations

from typing import Callable
import collections
import time

from soar_sdk.SiemplifyLogger import SiemplifyLogger
from . import constants
from .datamodels import ListSecurityPolicy
from . import exceptions


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
