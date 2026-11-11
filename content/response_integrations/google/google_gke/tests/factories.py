import uuid
import factory
from faker import Factory as FakerFactory

from google_gke.core.GKEConsts import API_URL
from google_gke.core.GKEDatamodels import (
    KubeCluster,
    KubeClusterOperation,
    KubeClusterNodePool,
)
from google_gke.core.GKEManagers import GKEApiManager
from google_gke.core.GKEServices import (
    GKEClustersService,
    GKEOperationService,
    GKEClusterNodesService,
)
from integration_testing.logger import Logger

faker = FakerFactory.create()


class APIManagerFactory(factory.Factory):

    class Meta:
        model = GKEApiManager

    api_root = API_URL
    project_id = "test-project-id"


class ClustersServiceFactory(factory.Factory):

    class Meta:
        model = GKEClustersService

    api_manager = factory.SubFactory(APIManagerFactory)
    logger = Logger()
    zone_name = "test-zone"


class OperationServiceFactory(factory.Factory):

    class Meta:
        model = GKEOperationService

    api_manager = factory.SubFactory(APIManagerFactory)
    logger = Logger()
    zone_name = "test-zone"


class ClusterNodeServiceFactory(factory.Factory):

    class Meta:
        model = GKEClusterNodesService

    api_manager = factory.SubFactory(APIManagerFactory)
    logger = Logger()
    zone_name = "test-zone"
    cluster_name = "test-cluster-name"


class FactoryMixin(factory.Factory):
    _exclude_json_fields = ["raw_data"]

    @classmethod
    def _after_postgeneration(cls, obj, *args, **kwargs):
        super()._after_postgeneration(obj, *args, **kwargs)
        obj.raw_data = {
            k: v for k, v in obj.__dict__.items()
            if k not in cls._exclude_json_fields
        }


class ClustersFactory(FactoryMixin):

    class Meta:
        model = KubeCluster

    cluster_id = str(uuid.uuid4())
    name = factory.LazyFunction(faker.name)


class ClusterOperationsFactory(FactoryMixin):
    _exclude_json_fields = ["raw_data", "cluster_name"]

    class Meta:
        model = KubeClusterOperation

    name = factory.LazyFunction(faker.name)
    status = "RUNNING"


class ClusterNodePoolFactory(FactoryMixin):

    class Meta:
        model = KubeClusterNodePool

    name = factory.LazyFunction(faker.name)
