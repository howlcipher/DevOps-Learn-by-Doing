"""Cloud concepts taught independently of any one provider's naming.

concept -> provider implementation, not Azure == AWS == GCP: see
docs/adr/0006-concept-first-multi-cloud.md.
"""

from __future__ import annotations

from enum import Enum


class CloudConcept(Enum):
    MANAGED_KUBERNETES = "managed_kubernetes"
    CONTAINER_REGISTRY = "container_registry"
    VIRTUAL_NETWORK = "virtual_network"
    MANAGED_IDENTITY = "managed_identity"
    SECRETS_STORE = "secrets_store"
    OBJECT_STORAGE = "object_storage"
    LOG_ANALYTICS = "log_analytics"
    RESOURCE_GROUP = "resource_group"
