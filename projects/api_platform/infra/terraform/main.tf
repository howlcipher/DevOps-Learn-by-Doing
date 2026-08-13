# The resources this configuration declares: everything the learner sees
# planned/applied against Azure by `devops-learn terraform`.
#
# Tagged consistently so every resource this project creates is obvious in
# the Azure portal and easy to find and delete.

locals {
  tags = {
    project     = "devops-learn-by-doing"
    environment = "learning"
    managed-by  = "terraform"
    purpose     = "devops-learning"
  }

  # Azure Container Registry names must be alphanumeric only (no hyphens),
  # unlike most other Azure resource names -- strip them here rather than
  # relaxing var.project_name itself.
  registry_name = replace(var.project_name, "-", "")
}

resource "azurerm_resource_group" "main" {
  name     = "${var.project_name}-rg"
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

resource "azurerm_log_analytics_workspace" "main" {
  name                = "${var.project_name}-logs"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  sku                 = "PerGB2018"
  retention_in_days   = 30
  tags                = local.tags
}
