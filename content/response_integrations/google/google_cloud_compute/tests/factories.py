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
