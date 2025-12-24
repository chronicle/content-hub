from __future__ import annotations

import boto3

ec2 = boto3.resource("ec2", "us-east-1")
client = boto3.client("ec2", "us-east-1")
instance = ec2.Instance("id")

VALID_STATUS_CODES = (200,)

ec2_waiters_names = client.waiter_names


class EC2Manager:
    """Amazon EC2 Manager"""

    def __init__(
        self,
        aws_access_key,
        aws_secret_key,
        aws_default_region,
        verify_ssl=False,
    ):
        self.aws_access_key = aws_access_key
        self.aws_secret_key = aws_secret_key
        self.aws_default_region = aws_default_region

        session = boto3.session.Session()

        self.client = session.client(
            "ec2",
            aws_access_key_id=aws_access_key,
            aws_secret_access_key=aws_secret_key,
            region_name=aws_default_region,
            verify=verify_ssl,
        )

    def ec2_waiter(self, ec2_waiter_name, instances_id_list, dry_run=False):
        if ec2_waiter_name not in ec2_waiters_names:
            raise Exception(f"The waiter name fhould be one of:{ec2_waiters_names}")

        if not isinstance(instances_id_list, list):
            instances_id_list = instances_id_list.split()

        waiter = self.client.get_waiter(ec2_waiter_name)

        waiter.wait(
            # Filters=filters,
            InstanceIds=instances_id_list,
            DryRun=dry_run,
            # MaxResults=max_results,
            # NextToken=next_token,
            # WaiterConfig=waiter_config_dict
        )

    def test_connectivity(self):
        """Test connectivity with AWS EC2
        :return: True if the connection was successful, otherwise return False
        """
        response = self.client.describe_regions(DryRun=False)

        return response

    def start_instances(self, instances_id_list, dry_run=False):
        """Start an instance that was previously stopped
        :param instances_id_list:(list) The instance IDs list which you want to start.
        :param dry_run:(boolean) Checks whether you have the required permissions for the action, without actually making the request.
                Provides an error response. For more info: https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ec2.html#EC2.Client.start_instances
        :return:(dict) Information about the started instances.
        """
        if not isinstance(instances_id_list, list):
            instances_id_list = instances_id_list.split()

        response = self.client.start_instances(
            InstanceIds=instances_id_list,
            DryRun=dry_run,
        )

        return response

    def stop_instances(
        self,
        instances_id_list,
        hibernate=False,
        dry_run=False,
        force=False,
    ):
        """Stop an instance that was previously started
        :param instances_id_list:(list) The instance IDs list which you want to stop.
        :param hibernate:(boolean) If the instance was enabled for hibernation at launch
        :param dry_run:(boolean) Checks whether you have the required permissions for the action, without actually making the request.
                Provides an error response. For more info: https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ec2.html#EC2.Client.stop_instances
        :param force:(boolean) Forces the instances to stop
        :return: (dict) Information about the stopped instances.
        """
        if not isinstance(instances_id_list, list):
            instances_id_list = instances_id_list.split()

        response = self.client.stop_instances(
            InstanceIds=instances_id_list,
            Hibernate=hibernate,
            DryRun=dry_run,
            Force=force,
        )

        return response

    def describe_instances(self, instances_id_list=[], filters=[{}], max_results=1000):
        """Retrieve the specified instances or all instances.
        If you do not specify instance IDs or filters, the output includes information for all instances
        :param instances_id_list: (list) The instance IDs list which you want to fetch information for.
        :param filters: (list) The filters of the instances which you want to retrieve.
                        For more information: https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ec2.html#EC2.Client.describe_instances
        :param max_results:(integer) The maximum number between 5 to 1000 of results to return in a single call.
        :return: (dict) Information about the found instances.
        """
        if instances_id_list is None:
            response = self.client.describe_instances(
                Filters=filters,
                MaxResults=max_results,
            )
        else:
            if not isinstance(instances_id_list, list):
                instances_id_list = instances_id_list.split()

            response = self.client.describe_instances(
                Filters=filters,
                InstanceIds=instances_id_list,
            )

        return response

    def create_instance(
        self,
        image_id,
        instance_type,
        max_count,
        min_count,
        security_groups_id,
        dry_run=False,
    ):
        """Creating instance to a specific AMI ID
        :param image_id: (string) The ID of the AMI. An AMI ID is required to create an instance
        :param instance_type: (string) specify determines the hardware of the host computer used for your instance
        :param max_count (int) The maximum number of instances to create
        :param min_count (int) The maximum number of instances to create
        :param security_groups_id (list) The IDs of the security groups
        :param dry_run (boolean) Checks whether you have the required permissions for the action, without actually making the request
        :return: (dict) Information about the created instances.
        """
        if security_groups_id is None:
            security_groups_id = []

        if not isinstance(security_groups_id, list):
            security_groups_id = security_groups_id.split()

        if instance_type is None:
            instance_type = "m1.small"

        response = self.client.run_instances(
            ImageId=image_id,
            InstanceType=instance_type,
            MaxCount=max_count,
            MinCount=min_count,
            SecurityGroupIds=security_groups_id,
            DryRun=dry_run,
        )

        return response

    def delete_instance(self, instance_id, dry_run=False):
        """Delete an instance
        :param instance_id (list) The instances id you want to delete
        :param dry_run (boolean) Checks whether you have the required permissions for the action, without actually making the request.
        :return: (dict) Information about the deleted instances.
        """
        if not isinstance(instance_id, list):
            instance_id = instance_id.split()

        response = self.client.terminate_instances(
            InstanceIds=instance_id,
            DryRun=dry_run,
        )

        return response

    def create_tags(self, resources_ID, tags_list, dry_run=False):
        """Adds or overwrites only the specified tags for the specified Amazon EC2 resource or resources.
        When you specify an existing tag key, the value is overwritten with the new value.
        Each resource can have a maximum of 50 tags.
        Tag keys must be unique per resource.
        :param dry_run:(boolean) Checks whether you have the required permissions for the action, without actually making the request.
        :param tags_list: (list) The tags list, the value parameter is required.
        :param resources_ID: The IDs of the resources, separated by spaces.
        :return: (dict) Information about the created tags.
        """
        if not isinstance(resources_ID, list):
            resources_ID = resources_ID.split()

        response = self.client.create_tags(
            DryRun=dry_run,
            Resources=resources_ID,
            Tags=tags_list,
        )

        return response

    def authorize_security_group_egress(
        self,
        group_id,
        ip_permissions_list,
        dry_run=False,
    ):
        """Adds the specified egress rules to a security group for use with a VPC.
        :param dry_run:(boolean) Checks whether you have the required permissions for the action, without actually making the request.
        :param group_id: (string) The group id you want to authorize
        :param ip_permissions_list: (list) The IP permissions you want to provide to the given group_id
        :return: (dict) ResponseMetadata.
        """
        if not isinstance(ip_permissions_list, list):
            ip_permissions_list = ip_permissions_list.split()

        response = self.client.authorize_security_group_egress(
            DryRun=dry_run,
            GroupId=group_id,
            IpPermissions=ip_permissions_list,
        )
        return response

    def authorize_security_group_ingress(
        self,
        group_id,
        ip_permissions_list,
        dry_run=False,
    ):
        """Adds the specified ingress rules to a security group for use with a VPC.
        :param dry_run:(boolean) Checks whether you have the required permissions for the action, without actually making the request.
        :param group_id: (string) The group id you want to authorize
        :param ip_permissions_list: (list) The IP permissions you want to provide to the given group_id
        :return: (dict) ResponseMetadata.
        """
        if not isinstance(ip_permissions_list, list):
            ip_permissions_list = ip_permissions_list.split()

        response = self.client.authorize_security_group_ingress(
            GroupId=group_id,
            IpPermissions=ip_permissions_list,
            DryRun=dry_run,
        )

        return response

    def revoke_security_group_ingress(
        self,
        group_id,
        ip_permissions_list,
        dry_run=False,
    ):
        """Removes the specified ingress rules from a security group
        :param dry_run:(boolean) Checks whether you have the required permissions for the action, without actually making the request.
        :param group_id: (string) The group id you want to revoke permissions to
        :param ip_permissions_list: (list) The IP permissions you want to revoke to the given group_id
        :return: (dict) ResponseMetadata.
        """
        if not isinstance(ip_permissions_list, list):
            ip_permissions_list = ip_permissions_list.split()

        response = self.client.revoke_security_group_ingress(
            GroupId=group_id,
            IpPermissions=ip_permissions_list,
            DryRun=dry_run,
        )

        return response

    def revoke_security_group_egress(
        self,
        group_id,
        ip_permissions_list,
        dry_run=False,
    ):
        """Removes the specified egress rules from a security group
        :param dry_run:(boolean) Checks whether you have the required permissions for the action, without actually making the request.
        :param group_id: (string) The group id you want to revoke permissions to
        :param ip_permissions_list: (list) The IP permissions you want to revoke to the given group_id
        :return: (dict) ResponseMetadata.
        """
        if not isinstance(ip_permissions_list, list):
            ip_permissions_list = ip_permissions_list.split()

        response = self.client.revoke_security_group_egress(
            GroupId=group_id,
            IpPermissions=ip_permissions_list,
            DryRun=dry_run,
        )

        return response
