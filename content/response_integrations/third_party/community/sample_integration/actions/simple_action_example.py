from __future__ import annotations

import datetime as dt
import json
from typing import TYPE_CHECKING

from TIPCommon.base.action.data_models import DataTable, Link
from TIPCommon.extraction import extract_action_param
from TIPCommon.transformation import construct_csv
from TIPCommon.validation import ParameterValidator

from ..core.base_action import SampleAction
from ..core.constants import (
    SIMPLE_ACTION_EXAMPLE_SCRIPT_NAME,
    CurrenciesDDLEnum,
    TimeFrameDDLEnum,
)
from ..core.exceptions import SampleIntegrationInvalidParameterError

if TYPE_CHECKING:
    from typing import NoReturn

    from TIPCommon.types import JSON, SingleJson

    from ..core.data_models import DailyRates


DEFAULT_CURRENCIES_DDL: str = "Select One"
DEFAULT_TIME_FRAME: str = "Today"
DEFAULT_RETURN_JSON_RESULT: bool = True

SUCCESS_MESSAGE: str = (
    "Successfully returned information about the following currencies from "
    "{start_time} to {end_time} :\n{currencies}"
)
EXAMPLE_CASE_WALL_LINK: str = "https://api.vatcomply.com/rates?date={date}&base={base}"


class SimpleActionExample(SampleAction):
    def __init__(self) -> None:
        super().__init__(SIMPLE_ACTION_EXAMPLE_SCRIPT_NAME)

    def _extract_action_parameters(self) -> None:
        self.params.currencies_str = extract_action_param(
            self.soar_action,
            param_name="Currencies String",
            print_value=True,
        )
        self.params.currencies_ddl = extract_action_param(
            self.soar_action,
            param_name="Currencies DDL",
            default_value=DEFAULT_CURRENCIES_DDL,
            print_value=True,
        )
        self.params.time_frame = extract_action_param(
            self.soar_action,
            param_name="Time Frame",
            default_value=DEFAULT_TIME_FRAME,
            print_value=True,
        )
        self.params.start_time = extract_action_param(
            self.soar_action,
            param_name="Start Time",
            print_value=True,
        )
        self.params.end_time = extract_action_param(
            self.soar_action,
            param_name="End Time",
            print_value=True,
        )
        self.params.return_json_result = extract_action_param(
            self.soar_action,
            param_name="Return JSON Result",
            default_value=DEFAULT_RETURN_JSON_RESULT,
            input_type=bool,
            print_value=True,
        )

    def _validate_params(self) -> None:
        validator: ParameterValidator = ParameterValidator(self.soar_action)
        self._validate_currencies_params(validator)
        self._validate_time_params(validator)

    def _validate_currencies_params(self, validator: ParameterValidator) -> None:
        """Validate the provided currencies_str and currencies_ddl parameters
        & Sets `list[str]` currencies parameter based on them.

        Sets:
            self.params.currencies: `list[str]`
        """
        currencies: list[str] = validator.validate_csv(
            param_name="Currencies String",
            csv_string=self.params.currencies_str,
            print_value=True,
        )
        currency_ddl_option: str = validator.validate_ddl(
            param_name="Currencies DDL",
            value=self.params.currencies_ddl,
            ddl_values=CurrenciesDDLEnum.values(),
            print_value=True,
        )
        if currency_ddl_option not in currencies + [DEFAULT_CURRENCIES_DDL]:
            currencies.append(currency_ddl_option)
        if not currencies and currency_ddl_option == DEFAULT_CURRENCIES_DDL:
            raise SampleIntegrationInvalidParameterError(
                'at least "Currencies String" or "Currencies DDL" should have a value provided.'
            )
        self.params.currencies = currencies
        self.logger.info(f"Action is going to get data for currencies: {repr(currencies)}")

    def _validate_time_params(self, validator: ParameterValidator) -> None:
        """Validate the provided time_frame, start_time, end_time parameters
        & Sets `datetime.date` parameters based on them.

        Sets:
            self.params.start_date: `datetime.date`
            self.params.end_date: `datetime.date`
        """
        self.params.time_frame = validator.validate_ddl(
            param_name="Time Frame",
            value=self.params.time_frame,
            ddl_values=TimeFrameDDLEnum.values(),
            print_value=True,
        )
        time_frame = TimeFrameDDLEnum(self.params.time_frame)
        if time_frame != TimeFrameDDLEnum.CUSTOM:
            self.params.start_date = time_frame.to_start_date()
            self.params.end_date = dt.datetime.now().date()
            if self.params.start_time or self.params.end_time:
                self.logger.warn(
                    f"Time Frame is set to '{time_frame.value}'. "
                    "Ignoring 'Start Time' and 'End Time' parameters."
                )

        else:
            if not self.params.start_time:
                raise SampleIntegrationInvalidParameterError(
                    "'Start Time' must be provided if 'Time Frame' is set to 'Custom'",
                )

            self.params.start_date = dt.datetime.fromisoformat(
                self.params.start_time.replace("Z", "+00:00"),
            ).date()

            if self.params.end_time:
                self.params.end_date = dt.datetime.fromisoformat(
                    self.params.end_time.replace("Z", "+00:00")
                ).date()
            else:
                self.params.end_date = dt.datetime.now().date()

        if self.params.end_date - self.params.start_date > dt.timedelta(days=7):
            self.logger.warn(
                'The delta between "Start Time" and "End Time" can\'t be greater '
                'than 7 days. Adjusting "End Time" to be exactly 7 days after '
                '"Start Time"'
            )
            self.params.end_date = self.params.start_date + dt.timedelta(days=7)

        self.logger.info(f"Using start_time {repr(self.params.start_date)}")
        self.logger.info(f"Using end_time {repr(self.params.end_date)}")

    def _perform_action(self, _=None):
        exchange_rates: list[DailyRates] = self.api_client.get_rates(
            currencies=self.params.currencies,
            start_date=self.params.start_date,
            end_date=self.params.end_date,
        )
        json_results: list[SingleJson] = [rates.json() for rates in exchange_rates]
        if self.params.return_json_result:
            self.json_results = json_results
        self._create_data_tables(exchange_rates)
        self._create_links(exchange_rates)
        self._add_result_case_attachment(json_results)
        self.output_message: str = SUCCESS_MESSAGE.format(
            start_time=self.params.start_date,
            end_time=self.params.end_date,
            currencies=",".join(self.params.currencies),
        )

    def _create_data_tables(self, exchange_rates: list[DailyRates]) -> None:
        """Creates data tables from the given exchange rates and adds them to the
        data_tables attribute.

        Args:
            exchange_rates (list[DailyRates]): A list of DailyRates objects.
        """
        for daily_rates in exchange_rates:
            self.logger.info(f"Creating data tables for exchange date {daily_rates.date}")
            self.data_tables.extend(
                DataTable(
                    data_table=construct_csv(base_rate.to_csv()),
                    title=f"Currency: {base_rate.base} - {base_rate.date} Table",
                )
                for base_rate in daily_rates.exchange_rates
            )

    def _create_links(self, exchange_rates: list[DailyRates]) -> None:
        """Creates links from the given exchange rates and adds them to the
        links attribute.

        Args:
            exchange_rates (list[DailyRates]): A list of DailyRates objects.
        """
        for daily_rates in exchange_rates:
            self.links.extend(
                Link(
                    link=EXAMPLE_CASE_WALL_LINK.format(
                        date=base_rate.date,
                        base=base_rate.base,
                    ),
                    title=f"Currency: {base_rate.base} - {base_rate.date} Link",
                )
                for base_rate in daily_rates.exchange_rates
            )

    def _add_result_case_attachment(self, json_results: JSON) -> None:
        """Add the JSON results as an attachment to the current case.

        Args:
            json_results (JSON): The JSON results to be added as an attachment.
        """
        result_file_path: str = self.save_temp_file(
            filename="Result.json",
            content=json.dumps(json_results),
        )
        self._add_attachment_to_current_case(result_file_path)


def main() -> NoReturn:
    SimpleActionExample().run()


if __name__ == "__main__":
    main()
