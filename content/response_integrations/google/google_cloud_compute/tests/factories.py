import factory
from faker import Factory as FakerFactory

from google_cloud_compute.core.GoogleCloudComputeDatamodels import (
    FirewallRule,
    OperationResource,
    PatchJob,
)

faker = FakerFactory.create()


class FactoryMixin(factory.Factory):
    _exclude_json_fields = ["raw_data"]

    @classmethod
    def _after_postgeneration(cls, obj, *args, **kwargs):
        super()._after_postgeneration(obj, *args, **kwargs)
        obj.raw_data = {
            k: v for k, v in obj.__dict__.items()
            if k not in cls._exclude_json_fields
        }


class PatchJobFactory(FactoryMixin):
    class Meta:
        model = PatchJob

    name = "test-patch-job"
    description = factory.Faker("paragraph")
    display_name = factory.Faker("name")
    duration = "3600s"
    instance_filter = factory.DictFactory()
    patch_config = factory.DictFactory()
    rollout = factory.DictFactory()


class FirewallRuleFactory(FactoryMixin):
    class Meta:
        model = FirewallRule

    name = "test-firewall-rule"


class OperationFactory(FactoryMixin):
    _exclude_json_fields = ["raw_data"]

    class Meta:
        model = OperationResource

    status = "RUNNING"
