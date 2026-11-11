

def test_clusters_service_list(
        mocker,
        clusters_service_factory,
        clusters_factory,
):
    session = mocker.Mock()
    kube_clusters = [
        clusters_factory()
        for _ in range(2)
    ]
    clusters_service = clusters_service_factory(
        api_manager__session=session
    )

    mocker.patch.object(
        session,
        "get",
        return_value=mocker.Mock(
            status_code=200,
            json=lambda: {
                "clusters": [cluster.raw_data for cluster in kube_clusters]
            }
        )
    )

    assert (
        cluster_mock.__dict__ == cluster_response.__dict__
        for cluster_mock, cluster_response
        in zip(clusters_service.list(), kube_clusters)
    )


def test_clusters_service_get(
        mocker,
        clusters_service_factory,
        clusters_factory,
):
    session = mocker.Mock()
    kube_cluster = clusters_factory()
    clusters_service = clusters_service_factory(
        api_manager__session=session
    )

    mocker.patch.object(
        session,
        "get",
        return_value=mocker.Mock(
            status_code=200,
            json=lambda: kube_cluster.raw_data
        )
    )

    assert (
        kube_cluster.__dict__
        == clusters_service.get(kube_cluster.name).__dict__
    )


def test_clusters_service_update_labels(
        mocker,
        clusters_service_factory,
        cluster_operations_factory
):
    session = mocker.Mock()
    clusters_service = clusters_service_factory(
        api_manager__session=session
    )
    cluster_operation = cluster_operations_factory(
        zone=clusters_service.zone_name,
        cluster_name="test-cluster"
    )
    update_cluster = {
        "labelFingerprint": "fingerprint",
        "resourceLabels": {"test": "label"}
    }

    mocker.patch.object(
        session,
        "post",
        return_value=mocker.Mock(
            status_code=200,
            json=lambda: cluster_operation.raw_data
        )
    )
    result = clusters_service.update_labels(
        cluster_name="test-cluster",
        label_fingerprint=update_cluster["labelFingerprint"],
        labels=update_cluster["resourceLabels"]
    )

    assert session.post.call_args[1]["json"] == update_cluster
    assert (
        cluster_operation.__dict__ == result.__dict__
    )


def test_clusters_service_update_addons(
        mocker,
        clusters_service_factory,
        cluster_operations_factory
):
    session = mocker.Mock()
    clusters_service = clusters_service_factory(
        api_manager__session=session
    )
    cluster_operation = cluster_operations_factory(
        zone=clusters_service.zone_name,
        cluster_name="test-cluster"
    )
    update_cluster = {
        "addonsConfig": {
            "httpLoadBalancing": {
                "disabled": True
            },
            "horizontalPodAutoscaling": {
                "disabled": False
            },
            "networkPolicyConfig": {
                "disabled": True
            },
            "cloudRunConfig": {
                "disabled": True,
                "loadBalancerType": "LOAD_BALANCER_TYPE_UNSPECIFIED"
            },
            "configConnectorConfig": {
                "enabled": True
            }
        }
    }

    mocker.patch.object(
        session,
        "post",
        return_value=mocker.Mock(
            status_code=200,
            json=lambda: cluster_operation.raw_data
        )
    )
    result = clusters_service.update_addons(
        cluster_name="test-cluster",
        http_load_balancing_disabled=True,
        horizontal_pod_autoscaling_disabled=False,
        network_policy_config_disabled=True,
        cloud_run_config_disabled=True,
        cloud_run_config_load_balancer_type="LOAD_BALANCER_TYPE_UNSPECIFIED",
        config_connector_config_enabled=True
    )

    assert session.post.call_args[1]["json"] == update_cluster
    assert (
            cluster_operation.__dict__ == result.__dict__
    )


def test_operation_service_list(
        mocker,
        operation_service_factory,
        cluster_operations_factory,
):
    session = mocker.Mock()
    operations = [
        cluster_operations_factory()
        for _ in range(2)
    ]
    operation_service = operation_service_factory(
        api_manager__session=session
    )

    mocker.patch.object(
        session,
        "get",
        return_value=mocker.Mock(
            status_code=200,
            json=lambda: {
                "clusters": [cluster.raw_data for cluster in operations]
            }
        )
    )

    assert (
        operation_mock.__dict__ == operation_response.__dict__
        for operation_mock, operation_response
        in zip(operation_service.list(), operations)
    )


def test_operation_service_get(
        mocker,
        operation_service_factory,
        cluster_operations_factory,
):
    session = mocker.Mock()
    operation = cluster_operations_factory()
    clusters_service = operation_service_factory(
        api_manager__session=session
    )

    mocker.patch.object(
        session,
        "get",
        return_value=mocker.Mock(
            status_code=200,
            json=lambda: operation.raw_data
        )
    )

    assert (
        operation.__dict__
        == clusters_service.get(operation.name).__dict__
    )


def test_cluster_node_service_list(
        mocker,
        cluster_node_service_factory,
        cluster_node_pool_factory,
):
    session = mocker.Mock()
    node_pools = [
        cluster_node_pool_factory()
        for _ in range(2)
    ]
    node_pool_service = cluster_node_service_factory(
        api_manager__session=session
    )

    mocker.patch.object(
        session,
        "get",
        return_value=mocker.Mock(
            status_code=200,
            json=lambda: {
                "clusters": [node.raw_data for node in node_pools]
            }
        )
    )

    assert (
        node_mock.__dict__ == node_response.__dict__
        for node_mock, node_response
        in zip(node_pool_service.list(), node_pools)
    )


def test_cluster_node_service_get(
        mocker,
        cluster_node_service_factory,
        cluster_node_pool_factory,
):
    session = mocker.Mock()
    node_pool = cluster_node_pool_factory()
    cluster_node_service = cluster_node_service_factory(
        api_manager__session=session
    )

    mocker.patch.object(
        session,
        "get",
        return_value=mocker.Mock(
            status_code=200,
            json=lambda: node_pool.raw_data
        )
    )

    assert (
        node_pool.__dict__
        == cluster_node_service.get(node_pool.name).__dict__
    )


def test_operation_service_set_pool_autoscaling(
        mocker,
        cluster_node_service_factory,
        cluster_operations_factory,
):
    session = mocker.Mock()
    node_service = cluster_node_service_factory(
        api_manager__session=session
    )
    cluster_operation = cluster_operations_factory(
        zone=node_service.zone_name,
        cluster_name=node_service.cluster_name
    )
    update_pool = {
        "autoscaling": {
            "enabled": True,
            "minNodeCount": 1,
            "autoprovisioned": False
        }
    }

    mocker.patch.object(
        session,
        "post",
        return_value=mocker.Mock(
            status_code=200,
            json=lambda: cluster_operation.raw_data
        )
    )
    result = node_service.set_pool_autoscaling(
        node_pool_name="test-node-pool",
        autoscaling_enabled=True,
        min_node_count=True,
    )

    assert session.post.call_args[1]["json"] == update_pool
    assert (
        cluster_operation.__dict__ == result.__dict__
    )


def test_operation_service_set_pool_management(
        mocker,
        cluster_node_service_factory,
        cluster_operations_factory,
):
    session = mocker.Mock()
    node_service = cluster_node_service_factory(
        api_manager__session=session
    )
    cluster_operation = cluster_operations_factory(
        zone=node_service.zone_name,
        cluster_name=node_service.cluster_name
    )
    update_pool = {
        "management": {
            "autoUpgrade": True,
        }
    }

    mocker.patch.object(
        session,
        "post",
        return_value=mocker.Mock(
            status_code=200,
            json=lambda: cluster_operation.raw_data
        )
    )
    result = node_service.set_pool_management(
        node_pool_name="test-node-pool",
        auto_upgrade=True,
    )

    assert session.post.call_args[1]["json"] == update_pool
    assert (
        cluster_operation.__dict__ == result.__dict__
    )


def test_operation_service_set_pool_size(
        mocker,
        cluster_node_service_factory,
        cluster_operations_factory,
):
    session = mocker.Mock()
    node_service = cluster_node_service_factory(
        api_manager__session=session
    )
    cluster_operation = cluster_operations_factory(
        zone=node_service.zone_name,
        cluster_name=node_service.cluster_name
    )
    update_pool = {
        "nodeCount": 1
    }

    mocker.patch.object(
        session,
        "post",
        return_value=mocker.Mock(
            status_code=200,
            json=lambda: cluster_operation.raw_data
        )
    )
    result = node_service.set_pool_size(
        node_pool_name="test-node-pool",
        node_count=1,
    )

    assert session.post.call_args[1]["json"] == update_pool
    assert (
        cluster_operation.__dict__ == result.__dict__
    )
