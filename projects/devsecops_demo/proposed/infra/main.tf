resource "azurerm_network_security_rule" "public_administrative_access" {
  name                        = "demo-public-ssh"
  priority                    = 100
  direction                   = "Inbound"
  access                      = "Allow"
  protocol                    = "Tcp"
  source_port_range           = "*"
  destination_port_range      = "22"
  source_address_prefix       = "*"
  destination_address_prefix  = "*"
  resource_group_name         = "devsecops-demo"
  network_security_group_name = "demo-nsg"
}
