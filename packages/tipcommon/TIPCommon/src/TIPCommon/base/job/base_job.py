# Copyright 2025 Google LLC
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

import datetime
import json
from abc import ABC, abstractmethod
from typing import Generic

import requests
from SiemplifyJob import SiemplifyJob
from SiemplifyUtils import (
    convert_datetime_to_unix_time,
    convert_string_to_unix_time,
    convert_timezone,
    convert_unixtime_to_datetime,
    output_handler,
    unix_now,
    utc_now,
)

from ...consts import DATETIME_FORMAT, NONE_VALS, NUM_OF_MILLI_IN_SEC, UNIX_FORMAT
from ...data_models import Container, JobParamType
from ...exceptions import JobSetupError, ParameterExtractionError
from ...extraction import extract_job_param
from ...rest.soar_api import get_installed_jobs
from ...types import JSON, Contains, JsonString
from ...utils import (
    camel_to_snake_case,
    safe_cast_bool_value_from_str,
    safe_cast_int_value_from_str,
)
from ..interfaces import ApiClient, ScriptLogger
from ..utils import (
    create_logger,
    create_params_container,
    create_soar_job,
    get_param_value_from_vault,
    is_native,
    nativemethod,
)
from .consts import (
    JOB_ID_KEY,
    JOB_INSTANCES_PARSE_ERROR_MSG,
    PARAMETER_EXTRACTION_ERR_MSG,
)
from .data_models import JobParameter


class Job(ABC, Generic[ApiClient]):
    """A class that represent a Job script in Chronicle SOAR

    Properties:
        soar_job: the SDK SiemplifyJob object
        script_name: the name of the job's script
        job_start_time: The unix time when the job has stated running
        logger: A logger from the soar_job object
        params: A descriptor that contains the parameters of the job
        error_msg: The error message to display on script failure.
    """

    def __init__(self, name: str) -> None:
        self._name: str = name
        self._soar_job: SiemplifyJob = create_soar_job()
        self._params: Container = create_params_container()
        self._api_client: Contains[ApiClient] | None = None
        self._logger: ScriptLogger = create_logger(self._soar_job)

        self._job_start_time: int = -1
        self._error_msg: str = "Got exception on main handler."
        self.name_id: str = f"{self.soar_job.script_name}_{self.soar_job.unique_identifier}"

        self._soar_job.script_name = self._name

    # ==================== Job Properties ==================== #

    @property
    def soar_job(self) -> SiemplifyJob:
        return self._soar_job

    @property
    def api_client(self) -> Contains[ApiClient]:
        return self._api_client

    @property
    def name(self) -> str:
        return self._name

    @property
    def job_start_time(self) -> int:
        return self._job_start_time

    @property
    def logger(self) -> ScriptLogger:
        return self._logger

    @property
    def params(self) -> Container:
        return self._params

    @property
    def error_msg(self) -> str:
        return self._error_msg

    @error_msg.setter
    def error_msg(self, value: str) -> None:
        if isinstance(value, str):
            self._error_msg = value

    @job_start_time.setter
    def job_start_time(self, value: int) -> None:
        if isinstance(value, int) and value > 0:
            self._job_start_time = value

    # ==================== Abstract Methods ==================== #

    @abstractmethod
    def _init_api_clients(self) -> Contains[ApiClient]:
        """Initiate and return all the API clients used by the action"""
        raise NotImplementedError

    @abstractmethod
    def _perform_job(self) -> None:
        """Perform the main flow of the job

        Raises:
            NotImplementedError: If not overridden

        """
        raise NotImplementedError

    # ==================== Native Methods ==================== #

    @nativemethod
    def _validate_params(self) -> None:
        """Validate the parameters' values

        Examples::

        class MyJob(Job):
            ...

            def _validate_params(self) -> None:
                validator = ParameterValidator(self.soar_job)

                self.params.some_param = validator.validate_positive(
                    param_name='Some Param',
                    value=self.params.some_param
                )

        Raises:
            JobSetupError: If any of the parameters are invalid.

        """
        raise NotImplementedError

    @nativemethod
    def _finalize(self) -> None:
        """Perform finalize steps before the job script ends"""

    # ==================== Job Methods ==================== #

    @output_handler
    def start(self) -> None:
        """Executes the connector logic.

        Execution steps:

            1. Extracting job's script parameters from the SDK job object
            2. Validate parameters values
            3. Running the job's main logic

        Raises:
            ParameterExtractionError: Failed to extract the job's parameters
            JobSetupError: if any of the pre setup phases fail

        """
        self._start_job_clock()
        self.logger.info(
            f"==================== Starting Job - {self.name} - Execution ===================="
        )

        self.logger.info("-------------------- Main - Param Init --------------------")
        try:
            self._extract_job_params()

        except (requests.HTTPError, json.JSONDecodeError) as e:
            error_msg = (
                PARAMETER_EXTRACTION_ERR_MSG.format(error=e)
                if isinstance(e, requests.HTTPError)
                else JOB_INSTANCES_PARSE_ERROR_MSG.format(error=e)
            )
            self.logger.error(error_msg)
            self.logger.exception(e)
            raise ParameterExtractionError(error_msg) from e

        self.logger.info("-------------------- Main - Started --------------------")
        try:
            try:
                self._api_client: Contains[ApiClient] = self._init_api_clients()
                self.logger.info("Validating input parameters")
                if not is_native(self._validate_params):
                    self._validate_params()

            except Exception as e:
                raise JobSetupError(e) from e

            self._perform_job()

        except Exception as error:
            self.logger.info("-------------------- Main - Failed --------------------")
            self.logger.error(f"{self.error_msg}")
            self.logger.exception(error)
            # Fix this behavior of job status in SDK/Python service
            raise RuntimeError from error

        finally:
            if not is_native(self._finalize):
                self.logger.info("Starting job finalizing steps")
                self._finalize()

        self.logger.info("-------------------- Main - Finished --------------------")

    # ==================== Protected Methods ==================== #

    def _get_case_context_property(
        self,
        case_id: str,
        property_key: str,
    ) -> JSON | JsonString | None:
        """Get case context property

        Args:
            case_id: The case ID to get the context from
            property_key: The key to look for under the case ID context

        Returns:
            The loaded value under the provided key in the case context

        """
        return self.soar_job.get_context_property(
            context_type=1,
            identifier=case_id,
            property_key=property_key,
        )

    def _set_case_context_property(
        self,
        case_id: str,
        property_key: str,
        property_value: str,
    ) -> None:
        """Set case context property

        Args:
            case_id: The case ID to set the context under
            property_key: The key to set in the case context
            property_value: The value to set under this key

        """
        self.soar_job.set_context_property(
            context_type=1,
            identifier=case_id,
            property_key=property_key,
            property_value=property_value,
        )

    def _extract_job_params(self) -> None:
        """Extract the job's parameters.

        Extracts the job's parameters from the UI
        and store them in the 'params' container.

        Note:
            Parameter names will be stored in snake_case format.

        """
        self.logger.info("Getting job parameters")
        params = self.__get_job_parameters()
        self.logger.info("Setting parameters as variables")
        for param in params:
            is_password = param.type_ == JobParamType.PASSWORD
            default_value = param.value

            input_type = str
            if param.type_ == JobParamType.BOOLEAN:
                input_type = bool
                default_value = safe_cast_bool_value_from_str(default_value)

            elif param.type_ == JobParamType.INTEGER:
                input_type = int
                default_value = safe_cast_int_value_from_str(default_value)

            vault_settings = self.soar_job.vault_settings
            value = extract_job_param(
                siemplify=self.soar_job,
                param_name=param.name,
                input_type=input_type,
                is_mandatory=param.is_mandatory,
                default_value=default_value,
                print_value=not is_password,
                remove_whitespaces=not is_password,
            )
            setattr(
                self.params,
                camel_to_snake_case(param.name),
                input_type(
                    value
                    if vault_settings is None
                    else get_param_value_from_vault(vault_settings, value)
                )
                if value not in NONE_VALS
                else value,
            )

    def _save_timestamp_by_unique_id(
        self,
        new_timestamp: int | datetime.datetime | None = None,
        timestamp_key: str | None = None,
    ) -> None:
        """Save Job timestamp under its unique ID

        Args:
            new_timestamp (int | datetime.datetime | None):
                The timestamp to save. Defaults to unix_now().
            timestamp_key (str):
                Context timestamp key. Default's to SOAR object timestamp key

        Raises:
            Exception: If failed to save the timestamp

        """
        if new_timestamp is None:
            new_timestamp = unix_now()

        if timestamp_key is None:
            timestamp_key = self.soar_job.TIMESTAMP_KEY

        if isinstance(new_timestamp, datetime.datetime):
            new_timestamp = convert_datetime_to_unix_time(new_timestamp)

        try:
            self.soar_job.set_job_context_property(
                identifier=self.name_id,
                property_key=timestamp_key,
                property_value=json.dumps(new_timestamp),
            )
        except Exception as e:
            raise RuntimeError(f"Failed saving timestamps to db, ERROR: {e}") from e

    def _fetch_timestamp_by_unique_id(
        self,
        datetime_format: bool = False,
        timezone: bool = False,
        timestamp_key: str | None = None,
    ) -> int | datetime.datetime:
        """Fetch Job timestamp by using its unique ID

        Args:
            datetime_format (bool):
                Whether to fetch it in datetime format. Defaults to False.
            timezone (bool):
                Whether to convert timezone. Defaults to False.
            timestamp_key (str):
                Context timestamp key. Default's to SOAR object timestamp key

        Raises:
            Exception: If failed to read the timestamp from the DB.

        Returns:
            int | datetime.datetime: The job's timestamp.

        """
        if timestamp_key is None:
            timestamp_key = self.soar_job.TIMESTAMP_KEY

        try:
            last_run_time = self.soar_job.get_job_context_property(
                identifier=self.name_id,
                property_key=timestamp_key,
            )
        except Exception as e:
            raise RuntimeError(f"Failed reading timestamps from db, ERROR: {e}") from e

        if last_run_time is None:
            last_run_time = 0

        try:
            last_run_time = int(last_run_time)

        except (ValueError, TypeError):
            last_run_time = convert_string_to_unix_time(last_run_time)

        if datetime_format:
            last_run_time = convert_unixtime_to_datetime(last_run_time)

            # SiemplifyUtils.convert_timezone is unsupported for DST,
            # so was removed
            if timezone:
                last_run_time = convert_timezone(last_run_time, timezone)
        else:
            last_run_time = int(last_run_time)

        return last_run_time

    def _get_job_last_success_time(
        self,
        offset_with_metric: dict[str, int],
        time_format: int = DATETIME_FORMAT,
        print_value: bool = True,
        microsec: bool = False,
        timestamp_key: str | None = None,
    ) -> int | datetime.datetime:
        """Get last success time datetime.

        Args:
            offset_with_metric (dict): The metric and value. Ex: {'hours': 1}
            time_format (int):
                The format of the output time.
                Use TIPCommon.constants.DATETIME_FORMAT
                or TIPCommon.constants.UNIX_FORMAT
            print_value (bool):
                Whether to log the value or not. Defaults to True.
            microsec (bool):
                Whether to divide the result by 1,000 in case the unix result is
                in microseconds and the desired result should be in milliseconds
            timestamp_key (str):
                Context timestamp key. Default's to SOAR object timestamp key

        Returns:
            int | datetime.datetime: The last success time.

        """
        last_run_timestamp = self._fetch_timestamp_by_unique_id(
            datetime_format=True, timestamp_key=timestamp_key
        )
        offset = datetime.timedelta(**offset_with_metric)
        current_time = utc_now()
        # Take more recent between last run and offset time
        datetime_result = max(current_time - offset, last_run_timestamp)
        unix_result = convert_datetime_to_unix_time(datetime_result)

        if microsec:
            unix_result //= NUM_OF_MILLI_IN_SEC

        if print_value:
            self.logger.info(f"Last success time. Date time:{datetime_result}. Unix:{unix_result}")

        return unix_result if time_format == UNIX_FORMAT else datetime_result

    def _start_job_clock(self) -> None:
        if self.job_start_time == -1:
            self.job_start_time = unix_now()

    # ==================== Private Methods ==================== #

    def __get_job_parameters(self) -> list[JobParameter]:
        """Get a job extracted parameters

        Raises:
            ParameterExtractionError: If fails to extract the parameters

        Returns:
            A list of JobParameter objects

        """
        job_id = self.soar_job.unique_identifier

        self.logger.info(f"Searching for the job instance of {job_id}")
        installed_jobs_response = get_installed_jobs(self.soar_job)
        if isinstance(installed_jobs_response, dict) and "job_instances" in installed_jobs_response:
            job_instances = installed_jobs_response["job_instances"]
        else:
            job_instances = installed_jobs_response

        for job_instance in job_instances:
            if job_instance.get(JOB_ID_KEY) == job_id:
                parameters = job_instance.get("parameters")
                if parameters is not None:
                    return [JobParameter(p) for p in parameters]

                job_instance_id = job_instance.get("id")
                if job_instance_id:
                    full_job_details = get_installed_jobs(
                        chronicle_soar=self.soar_job,
                        job_instance_id=job_instance_id,
                    )
                    return [JobParameter(p) for p in full_job_details.get("parameters", [])]

        # If we didn't return and got to this point the job is not installed
        raise ParameterExtractionError(
            f"The job {self.name} instance (id {job_id}) was not found!"
            "\nCustom/copy jobs - Make sure you saved the job, toggled it on "
            "and saved its instance at least once before running it "
            "and after each parameter change!"
        )
