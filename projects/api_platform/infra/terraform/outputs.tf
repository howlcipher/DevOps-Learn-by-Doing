output "resource_group_name" {
  value = azurerm_resource_group.main.name
}

output "container_registry_login_server" {
  value = azurerm_container_registry.main.login_server
}

output "container_app_environment_name" {
  value = azurerm_container_app_environment.main.name
}

output "container_app_name" {
  value = try(azurerm_container_app.api[0].name, null)
}

output "container_app_endpoint" {
  value = try("https://${azurerm_container_app.api[0].ingress[0].fqdn}", null)
}
