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

# ============================= IMPORTS ===================================== #
from __future__ import annotations
from soar_sdk.SiemplifyConnectors import CaseInfo
from TIPCommon import dict_to_flat

from .constants import VENDOR, PRODUCT, DEFAULT_NAME, WILDCARD, PRIORITIES


class ZabbixConnector:

    def __init__(self, connector_scope, zabbix_manager, tags={}):
        self.connector_scope = connector_scope
        self.logger = connector_scope.LOGGER
        self.zabbix_manager = zabbix_manager
        self.tags = tags

    @staticmethod
    def parse_whitelist_tags(whitelist):
        """
        Parse the tags from the whitelist
        :param whitelist: {list} The whitelist of the connector
        :return: {dict} The collected tags
        """
        tags = {}

        # Collect tags from whitelist
        for item in whitelist:
            tag, value = item.split(":")
            tags[tag] = value

        return tags

    def get_triggers(self, last_success_time_ms, only_problematic=False):
        """
        Get alerts from Zabbix
        :param: last_success_time_ms: {int} Get only triggers that have changed
            their state after the given time (unix timestamp)
        :param: only_problematic: {bool} If set to true
            consider only triggers in problem state.
        :return: {list} List of found triggers
        """
        triggers = []

        # Get problematic triggers with their last event
        # and filter them by given tags
        for trigger in self.zabbix_manager.get_triggers(
            problematic=only_problematic,
            select_last_event=True,
            last_change_since=last_success_time_ms / 1000,
        ):
            try:
                if self.tags:
                    # There are tags to filter
                    self.logger.info("Validating trigger against whitelisted tags.")

                    for tag_obj in trigger.get("tags", []):
                        tag = tag_obj.get("tag")
                        value = tag_obj.get("value")

                        if tag in list(self.tags.keys()) and (
                            value in self.tags[tag] or self.tags[tag] == WILDCARD
                        ):
                            # Trigger has passed the tags filter
                            self.logger.info(
                                f"Trigger {trigger.get('triggerid')} "
                                "has a whitelisted tag."
                            )
                            triggers.append(trigger)
                            break
                    else:
                        self.logger.info(
                            f"Trigger {trigger.get('triggerid')} doesn't have "
                            "a whitelisted tag. Skipping"
                        )

                else:
                    triggers.append(trigger)

            except Exception as e:
                self.logger.error(
                    f"Unable to process trigger {trigger.get('triggerid')}"
                )
                self.logger.exception(e)

        return triggers

    def get_trigger_last_event(self, trigger):
        """
        Get the last event of a given trigger
        :param trigger: {dict} The trigger info
        :return: {dict} The last event of the trigger
        """
        # Get the last event of the trigger and get its info
        event_id = trigger["lastEvent"]["eventid"]
        trigger_events = self.zabbix_manager.get_events(eventids=event_id)

        if not trigger_events:
            self.logger.info(
                f"No events found for trigger {trigger['triggerid']}. Skipping."
            )
            return

        event = trigger_events[0]
        event["trigger"] = trigger

        return event

    def get_events(self, triggers, is_test=False):
        """
        Get the events from the found triggers
        :param triggers: {list} The found triggers
        :param is_test: {bool} Whether this is a test run or not
        :return: {list} The events
        """
        events = []

        for trigger in triggers:
            try:
                event = self.get_trigger_last_event(trigger)

                if event and event not in events:
                    events.append(event)

            except Exception as e:
                self.logger.error(
                    "Unable to get events for trigger " f"{trigger.get('triggerid')}"
                )
                self.logger.exception(e)

                if is_test:
                    raise

        return events

    def create_alert_info(self, event, is_test=False):
        """
        Create a CaseInfo from an event
        :param event: {dict} The event data
        :param is_test: {bool} Whether this is a test run or not
        :return: {CaseInfo} The newly created case info
        """
        # Create the alert
        case_info = CaseInfo()
        maintenance = False

        try:
            hosts = []

            for host in event["hosts"]:
                host = self.zabbix_manager.get_hosts(hostids=host["hostid"])[0]

                if int(host.get("maintenance_status", 0)) == 1:
                    # Host is in maintenance - skip the event
                    maintenance = True

                hosts.append(host)

            event["hosts"] = hosts

        except Exception as e:
            self.logger.error(f"Unable to get hosts for alert {event['eventid']}")
            self.logger.exception(e)

            if is_test:
                raise

        if maintenance:
            # Skip the event
            self.logger.info(
                "One or more of the event's host are in maintenance. " "Skipping event."
            )
            return

        try:
            name = event["trigger"]["description"]
        except Exception as e:
            self.logger.error(f"Unable to get alert name for {event['eventid']}")
            self.logger.exception(e)
            name = DEFAULT_NAME

        case_info.name = name
        case_info.identifier = event["eventid"]

        case_info.ticket_id = case_info.identifier
        case_info.reason = case_info.name

        try:
            priority = PRIORITIES[event["trigger"]["priority"]]
        except Exception as e:
            self.logger.error(f"Unable to get priority for {event['eventid']}")
            self.logger.exception(e)
            priority = -1

        case_info.priority = priority
        case_info.device_vendor = VENDOR
        case_info.device_product = PRODUCT
        case_info.source_system_name = "Custom"
        case_info.display_id = case_info.identifier

        case_info.rule_generator = case_info.name  # Expression is too long...
        case_info.environment = self.connector_scope.context.connector_info.environment

        self.connector_scope.LOGGER.info("Flattening event's data")

        # Flatter specific areas of the dict
        event = dict_to_flat(event)

        case_info.events = [event]

        # Timestamps in Zabbix are in seconds and not milliseconds
        event["start_time"] = event["end_time"] = int(event.get("clock", 1)) * 1000
        case_info.start_time = case_info.end_time = int(event.get("clock", 1)) * 1000

        return case_info
