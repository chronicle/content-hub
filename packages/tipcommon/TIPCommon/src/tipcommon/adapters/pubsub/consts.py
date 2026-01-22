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

from ...exceptions import (
    AlreadyExistsError,
    BadGatewayError,
    DeadlineExceededError,
    FailedPreconditionError,
    InvalidArgumentError,
    NotFoundError,
    PermissionDeniedError,
    ResourceExhaustedError,
    UnauthenticatedError,
    UnavailableError,
)

PUBSUB_API_ROOT = "https://pubsub{rep_subdomain}.googleapis.com"
PUBSUB_SCOPE = "https://pubsub.googleapis.com/"
PUBSUB_RESOURCE_TEMPLATE = "projects/{project_id}/{resource_type}/{resource_name}"
PUBSUB_ENDPOINTS = {
    "topic": "v1/projects/{project_id}/topics/{topic_name}",
    "subscription": "v1/projects/{project_id}/subscriptions/{sub_name}",
    "publish": "v1/projects/{project_id}/topics/{topic_name}:publish",
    "pull": "v1/projects/{project_id}/subscriptions/{sub_name}:pull",
    "ack": "v1/projects/{project_id}/subscriptions/{sub_name}:acknowledge",
}
PUBSUB_ERROR_STATUS_MAPPING = {
    "ALREADY_EXISTS": AlreadyExistsError,
    "NOT_FOUND": NotFoundError,
    "BAD_GATEWAY": BadGatewayError,
    "DEADLINE_EXCEEDED": DeadlineExceededError,
    "INVALID_ARGUMENT": InvalidArgumentError,
    "PERMISSION_DENIED": PermissionDeniedError,
    "UNAUTHENTICATED": UnauthenticatedError,
    "UNAVAILABLE": UnavailableError,
    "RESOURCE_EXHAUSTED": ResourceExhaustedError,
    "FAILED_PRECONDITION": FailedPreconditionError,
}
PUBSUB_FIELD_MASK_MAPPING = {
    "topic": "topic",
    "push_config": "pushConfig",
    "bigquery_config": "bigqueryConfig",
    "cloud_storage_config": "cloudStorageConfig",
    "ack_deadline_seconds": "ackDeadlineSeconds",
    "retain_acked_messages": "retainAckedMessages",
    "retention_duration": "messageRetentionDuration",
    "labels": "labels",
    "enable_message_ordering": "enableMessageOrdering",
    "expiration_policy": "expirationPolicy",
    "filter": "filter",
    "dead_letter_policy": "deadLetterPolicy",
    "return_policy": "retryPolicy",
    "detached": "detached",
    "enable_once_delivery": "enableExactlyOnceDelivery",
    "message_storage_policy": "messageStoragePolicy",
    "kms_key_name": "kmsKeyName",
    "schema_settings": "schemaSettings",
    "satisfies_pzs": "satisfiesPzs",
}
