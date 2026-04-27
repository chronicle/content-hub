from __future__ import annotations

from typing import Any

import os

from .TrendVisionOneManager import TrendVisionOneManager
from .TrendVisionOneExceptions import TrendVisionOneException

from .constants import GLOBAL_TIMEOUT_THRESHOLD_IN_MIN
from . import datamodels



def get_entity_original_identifier(entity: Any) -> str:
    """
    Helper function for getting entity original identifier
    Args:
        entity: entity from which function will get original identifier

    Returns:
        original identifier
    """
    return entity.additional_properties.get("OriginalIdentifier", entity.identifier)


def check_submit_files_in_system(files: list) -> list:
    """Return not accessible or not found files in filesystem.

    Args:
        files (list): list of files.

    Returns:
        list: list of not found files.
    """
    not_found_files = [
        file
        for file in files
        if not (os.path.exists(file) and os.access(file, os.R_OK))
    ]

    return not_found_files


def is_async_action_global_timeout_approaching(siemplify, start_time):
    return (
        siemplify.execution_deadline_unix_time_ms - start_time
        < GLOBAL_TIMEOUT_THRESHOLD_IN_MIN * 60 * 1000
    )


def process_agents(
    manager: TrendVisionOneManager,
    agent_uids: list[str],
) -> datamodels.AgentResult:
    """Process a list of agent UUIDs, searching for each agent and categorizing them as
    successful or failed.

    Args:
        manager (TrendVisionOneManager): An instance of the TrendVisionOneManager for
        interacting with the API.
        agent_uids (list[str]): A list of agent UUIDs to process.

    Returns:
        AgentResult: An object containing two lists: `successful_agents`
        (list of Endpoint objects) and `failed_agents` (list of agent UUIDs
        that could not be processed).
    """
    agent_result: datamodels.AgentResult = datamodels.AgentResult([], [])
    for agent_id in agent_uids:
        try:
            if (agent := manager.search_endpoint(agent_id=agent_id)) is not None:
                agent_result.successful_agents.append(agent)
            else:
                agent_result.failed_agents.append(agent_id)
                manager.siemplify.LOGGER.info(f"Agent UUID not found: {agent_id}")

        except TrendVisionOneException as e:
            agent_result.failed_agents.append(agent_id)
            manager.siemplify.LOGGER.error(f"An error occurred on agent: {agent_id}")
            manager.siemplify.LOGGER.exception(e)

    return agent_result
