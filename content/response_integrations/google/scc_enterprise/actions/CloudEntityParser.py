from __future__ import annotations

import re
from typing import Any

from soar_sdk.SiemplifyDataModel import Alert
from TIPCommon.base.action import Action, EntityTypesEnum
from TIPCommon.data_models import CreateEntity
from TIPCommon.rest.soar_api import create_entity
from TIPCommon.types import Entity

from scc_enterprise.core.SCCEnterpriseConsts import CLOUD_ENTITY_PARSER_SCRIPT_NAME
from scc_enterprise.core.SCCEnterpriseUtils import parse_project_from_sa


EVENT_PRINCIPAL_EMAIL_KEY = "event_principal_user_emailAddresses"
EVENT_TARGET_EMAIL_KEY = "event_target_user_emailAddresses"
SA_EMAIL_RE_PATTERN = re.compile(r"@[\w\-_0-9]+.iam.gserviceaccount.com")
SA_RESOURCE_FORMAT = "//iam.googleapis.com/projects/{}/serviceAccounts/{}"
ADDITIONAL_PROPERTY_GCP_RESOURCE_NAME = "GCP_ResourceName"
ADDITIONAL_PROPERTY_AWS_EC2_SHORTNAME = "AWS_EC2_ShortName"

EVENT_AWS_REGION = "event_target_location_name"
EVENT_AWS_ACCOUNT_ID = "event_target_resource_attribute_labels_Recipient Account Id"

AWS_USER_ARN_PATTERN = re.compile(r"^arn:aws:iam::\d{12}:user/[\w+=,.@-]{1,64}$")
AWS_ROOT_USER_ARN_PATTERN = re.compile(r"^arn:aws:iam::\d{12}:root$")
AWS_S3_BUCKET_ARN_PATTERN = re.compile(r"^arn:aws:s3:::[a-z0-9.-]{3,63}$")
AWS_EC2_NAME_MACHINE_PATTERN = re.compile(r"^i-[a-f0-9]{8,17}$")
AWS_EC2_NAME_MACHINE_EXTRACT_PATTERN = re.compile("i-[a-f0-9]{8,17}")
AWS_EC2_ARN_MACHINE_PATTERN = re.compile(
    r"^arn:aws:ec2:[a-z0-9-]+:\d{12}:instance/i-[a-f0-9]{8,17}$"
)
AWS_GUARDDUTY_ARN_PATTERN = re.compile(
    r"^arn:aws:guardduty:[a-z0-9-]+:\d{12}:detector/"
    r"[a-zA-Z0-9-]+/finding/[a-zA-Z0-9-]+$"
)
AWS_ARN_PATTERN = re.compile(r"^arn:aws:[a-zA-Z0-9-:/]+")

# Azure
AZURE_RESOURCE_PATTERN = re.compile(r"^/subscriptions/.*?/providers/Microsoft\.")


def parse_ec2_instance_full_arn(instance_name: str, current_alert: Alert) -> str:
    """Parse AWS EC2 Instnace full ARN

    Args:
        instance_name (str): Instance name
        current_alert (SiemplifyDataModel.Alert): Current alert object

    Returns:
        str: ARN qualified instrance name
    """
    region = None
    account_id = None
    for security_event in current_alert.security_events:
        if EVENT_AWS_REGION in security_event.additional_properties:
            region = security_event.additional_properties[EVENT_AWS_REGION]
        if EVENT_AWS_ACCOUNT_ID in security_event.additional_properties:
            account_id = security_event.additional_properties[EVENT_AWS_ACCOUNT_ID]

    if region and account_id:
        return f"arn:aws:ec2:{region}:{account_id}:instance/{instance_name}"

    return instance_name


class CloudEntityParser(Action):
    def _init_api_clients(self) -> Any | None:
        pass

    def get_entity(
        self, entity_identifier: str, entity_type: EntityTypesEnum
    ) -> Entity | None:
        """Retrieves full entity data by identifier and type.

        Args:
            entity_identifier (str): Identifier of the entity.
            entity_type (str): Type of the entity.

        Returns:
            Entity | None: Entity data.
        """
        for entity in self.soar_action.target_entities:
            target_entity_id = entity.identifier.strip().encode()
            target_entity_type = entity.entity_type.encode()

            if (
                target_entity_id.lower() == entity_identifier.lower().encode()
                and target_entity_type == entity_type.value.encode()
            ):
                return entity
        return None

    def create_entity_relationship_by_entity(
        self,
        entity_name: str,
        entity_type: EntityTypesEnum,
        linked_entity_name: str,
        is_primary_link: bool = False,
        is_directional: bool = False,
    ) -> None:
        """Creates entity a link between two entites.

        Args:
            entity_name (str):
                Identifier of the entity 1 .
            linked_entity_name(str):
                Identifier of the entity 2.
            entity_type (EntityTypesEnum):
                Type of the entity 1.
            is_primary_link (bool, optional):
                isPrimaryLink property of the relationship. Defaults to False.
            is_directional (bool, optional):
                isDirectional property of the relationship. Defaults to False.
        """
        entity_to_create = CreateEntity(
            case_id=self.soar_action.case_id,
            alert_identifier=self.soar_action.current_alert.identifier,
            entity_type=entity_type.value,
            entity_identifier=entity_name,
            entity_to_connect_regex=f"{re.escape(str(linked_entity_name))}$",
            types_to_connect=[],
            is_primary_link=is_primary_link,
            is_directional=is_directional,
        )
        create_entity(self.soar_action, entity_to_create)

    def upsert_entity(
        self,
        entity_name: str,
        entity_type: EntityTypesEnum,
        additional_properties: dict[str, Any] | None = None,
    ) -> None:
        """Updates or creates entity in the case.

        Args:
            entity_name (str):
                Identifier of the entity.
            entity_type (EntityTypesEnum):
                Type of the entity.
            additional_properties (dict[str, Any], optional):
                Additional properties to be added to the entity. Defaults to {}.
        """
        if additional_properties is None:
            additional_properties = {}

        entity = self.get_entity(entity_name.strip(), entity_type)
        if entity is not None:
            entity.additional_properties.update(additional_properties)
            self.soar_action.update_entities([entity])
            self.logger.info(
                f"Entity with identifier {entity_name} hasn't been added to the "
                "case, as it already exists."
            )

        else:
            self.logger.info(f"Creating Entity with identifier {entity_name}")
            self._add_entity_to_case(
                entity_identifier=entity_name,
                entity_type=entity_type,
                is_internal=True,
                is_suspicious=False,
                is_enriched=False,
                is_vulnerable=False,
                properties=additional_properties,
            )

    def upsert_sa_entities(self) -> dict[str, EntityTypesEnum]:
        """Updates or creates GCP Service Account entities in the SOAR Alert.

        Returns:
            dict[str, EntityTypesEnum]: Dictionary of entities that were updated.
        """
        processed_entities = {}
        email_addresses = []

        for security_event in self.soar_action.current_alert.security_events:
            if EVENT_PRINCIPAL_EMAIL_KEY in security_event.additional_properties:
                email_addresses.extend(
                    security_event.additional_properties[
                        EVENT_PRINCIPAL_EMAIL_KEY
                    ].split(",")
                )
            if EVENT_TARGET_EMAIL_KEY in security_event.additional_properties:
                email_addresses.extend(
                    security_event.additional_properties[EVENT_TARGET_EMAIL_KEY].split(
                        ","
                    )
                )

        self.logger.info(f"Emails found: {', '.join(email_addresses)}")
        service_accounts_email_addresses = {
            e.replace("serviceAccount:", "")
            for e in email_addresses
            if SA_EMAIL_RE_PATTERN.search(e) is not None
        }
        self.logger.info(
            f"Service Accounts found: {', '.join(service_accounts_email_addresses)}"
        )

        service_accounts_email_addresses = list(service_accounts_email_addresses)
        for sa in service_accounts_email_addresses:
            project_name = parse_project_from_sa(sa)
            sa_resource_name = SA_RESOURCE_FORMAT.format(project_name, sa)
            self.upsert_entity(
                entity_name=sa,
                entity_type=EntityTypesEnum.USER,
                additional_properties={
                    ADDITIONAL_PROPERTY_GCP_RESOURCE_NAME: sa_resource_name
                },
            )
            processed_entities[sa] = EntityTypesEnum.USER
        return processed_entities

    @staticmethod
    def get_entity_type_from_event_property(
        property_key: str, property_value: str
    ) -> EntityTypesEnum | None:
        """Discerns the entity type from the SOAR event property.

        Args:
            property_key (str): Event property key
            property_value (str): Event property value

        Returns:
            EntityTypesEnum | None: Entity type. If the entity type cannot be discerned,
                None is returned.
        """
        if property_value.startswith("//cloudresourcemanager.googleapis.com/"):
            return EntityTypesEnum.DEPLOYMENT
        if property_value.startswith("//storage.googleapis.com/"):
            return EntityTypesEnum.DATABASE
        if property_value.startswith("//compute.googleapis.com/"):
            if "/instances/" in property_value:
                return EntityTypesEnum.HOST_NAME
            return EntityTypesEnum.DEPLOYMENT
        if property_value.startswith("//bigquery.googleapis.com/"):
            return EntityTypesEnum.DATABASE
        if property_value.startswith("//k8s.io") and "/clusterroles/" in property_value:
            return EntityTypesEnum.DEPLOYMENT
        if property_value.startswith("//container.googleapis.com/"):
            return EntityTypesEnum.CONTAINER
        if property_value.startswith("//iam.googleapis.com/"):
            return EntityTypesEnum.USER
        if property_value.startswith("//accesscontextmanager.googleapis.com/"):
            return EntityTypesEnum.DEPLOYMENT
        if property_value.startswith("//cloudsql.googleapis.com/"):
            return EntityTypesEnum.DATABASE

        if AWS_USER_ARN_PATTERN.match(property_value):
            return EntityTypesEnum.USER
        if AWS_ROOT_USER_ARN_PATTERN.match(property_value):
            return EntityTypesEnum.USER
        if AWS_S3_BUCKET_ARN_PATTERN.match(property_value):
            return EntityTypesEnum.DATABASE
        if AWS_EC2_NAME_MACHINE_PATTERN.match(property_value):
            return EntityTypesEnum.HOST_NAME
        if AWS_EC2_ARN_MACHINE_PATTERN.match(property_value):
            return EntityTypesEnum.HOST_NAME
        if AWS_ARN_PATTERN.match(
            property_value
        ) and not AWS_GUARDDUTY_ARN_PATTERN.match(property_value):
            return EntityTypesEnum.DEPLOYMENT
        if AZURE_RESOURCE_PATTERN.match(property_value):
            return EntityTypesEnum.DEPLOYMENT

        # generic fallbacks (legacy)
        if property_key == "entity_entity_hostname":
            return EntityTypesEnum.HOST_NAME
        if property_key == "event_target_resource_name":
            return EntityTypesEnum.DEPLOYMENT
        return None

    def _perform_action(self, __=None, _=None) -> None:
        processed_entities = {}
        processed_entities.update(self.upsert_sa_entities())
        aws_users = set()
        ec2_instances = set()
        s3_buckets = set()
        for security_event in self.soar_action.current_alert.security_events:
            for key, values in security_event.additional_properties.items():
                values_list = values.split(",")
                for value in values_list:
                    if value not in processed_entities:
                        entity_type = self.get_entity_type_from_event_property(
                            key, value
                        )
                        if entity_type is not None:
                            if AWS_ARN_PATTERN.match(
                                value
                            ) or AWS_EC2_NAME_MACHINE_PATTERN.match(value):
                                if AWS_ARN_PATTERN.match(value):  # arn:aws:
                                    properties = {}
                                    if AWS_EC2_ARN_MACHINE_PATTERN.match(value):
                                        instance_name = (
                                            AWS_EC2_NAME_MACHINE_EXTRACT_PATTERN.search(
                                                value
                                            )
                                        )
                                        properties = {
                                            ADDITIONAL_PROPERTY_AWS_EC2_SHORTNAME: (
                                                instance_name.group()
                                            )
                                        }
                                elif AWS_EC2_NAME_MACHINE_PATTERN.match(
                                    value
                                ):  # i-12345567
                                    properties = {
                                        ADDITIONAL_PROPERTY_AWS_EC2_SHORTNAME: value
                                    }
                                    value = parse_ec2_instance_full_arn(
                                        value, self.soar_action.current_alert
                                    )

                                if entity_type == EntityTypesEnum.HOST_NAME:
                                    ec2_instances.add(value)
                                elif entity_type == EntityTypesEnum.DATABASE:
                                    s3_buckets.add(value)
                                elif entity_type == EntityTypesEnum.USER:
                                    aws_users.add(value)
                            elif AZURE_RESOURCE_PATTERN.match(value):  # Azure
                                properties = {}
                            else:  # GCP
                                properties = {
                                    ADDITIONAL_PROPERTY_GCP_RESOURCE_NAME: value
                                }

                            self.logger.info(
                                f"Adding entity {value} of type {entity_type}"
                            )
                            self.upsert_entity(value, entity_type, properties)
                            processed_entities[value] = entity_type.value

        links = []
        # AWS relationships
        if ec2_instances:
            for user in aws_users:
                for ec2_instance in ec2_instances:
                    self.create_entity_relationship_by_entity(
                        ec2_instance.upper(), EntityTypesEnum.HOST_NAME, user.upper()
                    )
                    links.append([user, ec2_instance])
        if s3_buckets:
            for user in aws_users:
                for s3 in s3_buckets:
                    self.create_entity_relationship_by_entity(
                        s3.upper(), EntityTypesEnum.DATABASE, user.upper()
                    )
                    links.append([user, s3])

        self.logger.info(
            f"Processed entities: {', '.join([e for e in processed_entities])}"
        )
        self.json_results = {"created": processed_entities, "relationships": links}


if __name__ == "__main__":
    CloudEntityParser(CLOUD_ENTITY_PARSER_SCRIPT_NAME).run()
