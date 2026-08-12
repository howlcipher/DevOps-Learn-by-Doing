# Which platform Terraform talks to, and which version of it.
#
# Terraform merges every *.tf file in this directory into a single
# configuration -- providers.tf / variables.tf / main.tf / outputs.tf is a
# naming convention for readability, not a module boundary. See README.md.

terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.0"
    }
  }
}

provider "azurerm" {
  features {}
}
