resource "azurerm_network_security_rule" "administrative_access" {
  name                        = "demo-private-ssh"
  priority                    = 100
  direction                   = "Inbound"
  access                      = "Allow"
  protocol                    = "Tcp"
  source_port_range           = "*"
  destination_port_range      = "22"
  source_address_prefix       = "10.0.0.0/24"
  destination_address_prefix  = "10.0.0.4"
  resource_group_name         = "devsecops-demo"
  network_security_group_name = "demo-nsg"
}
