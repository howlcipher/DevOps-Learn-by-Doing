# The resources this configuration declares: everything the learner sees
# planned/applied against Azure by `devops-learn terraform`.
#
# Tagged consistently so every resource this project creates is obvious in
# the Azure portal and easy to find and delete.

locals {
  tags = {
    project     = "devops-learn-by-doing"
    environment = var.environment
    managed-by  = "terraform"
    purpose     = "devops-learning"
  }

  resource_prefix = "${var.project_name}-${var.environment}"

  # Azure Container Registry names must be alphanumeric only (no hyphens),
  # unlike most other Azure resource names -- strip them here rather than
  # relaxing var.project_name itself.
  registry_name = "${replace(local.resource_prefix, "-", "")}${substr(md5(data.azurerm_client_config.current.subscription_id), 0, 6)}acr"
}

data "azurerm_client_config" "current" {}

resource "azurerm_resource_group" "main" {
  name     = "${local.resource_prefix}-rg"
  location = var.location
  tags     = local.tags
}

resource "azurerm_container_registry" "main" {
  name                = "${local.registry_name}acr"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  sku                 = "Basic"
  tags                = local.tags
}

resource "azurerm_user_assigned_identity" "container_app" {
  name                = "${local.resource_prefix}-app-identity"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  tags                = local.tags
}

resource "azurerm_role_assignment" "container_app_acr_pull" {
  scope                = azurerm_container_registry.main.id
  role_definition_name = "AcrPull"
  principal_id         = azurerm_user_assigned_identity.container_app.principal_id
}

resource "azurerm_log_analytics_workspace" "main" {
  name                = "${local.resource_prefix}-logs"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  sku                 = "PerGB2018"
  retention_in_days   = 30
  tags                = local.tags
}

resource "azurerm_container_app_environment" "main" {
  name                       = "${local.resource_prefix}-env"
  resource_group_name        = azurerm_resource_group.main.name
  location                   = azurerm_resource_group.main.location
  log_analytics_workspace_id = azurerm_log_analytics_workspace.main.id
  tags                       = local.tags
}

resource "azurerm_container_app" "api" {
  count                        = var.deploy_application ? 1 : 0
  name                         = "${local.resource_prefix}-api"
  resource_group_name          = azurerm_resource_group.main.name
  container_app_environment_id = azurerm_container_app_environment.main.id
  revision_mode                = "Single"

  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.container_app.id]
  }

  registry {
    server   = azurerm_container_registry.main.login_server
    identity = azurerm_user_assigned_identity.container_app.id
  }

  ingress {
    external_enabled = true
    target_port      = 8000

    traffic_weight {
      latest_revision = true
      percentage      = 100
    }
  }

  template {
    min_replicas = 0
    max_replicas = 1

    container {
      name   = "api"
      image  = var.app_image
      cpu    = 0.25
      memory = "0.5Gi"
    }
  }

  tags = local.tags

  depends_on = [azurerm_role_assignment.container_app_acr_pull]
}
