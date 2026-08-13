variable "project_name" {
  description = "Short name used to prefix every resource this configuration creates."
  type        = string
  default     = "api-platform"
}

variable "location" {
  description = "Azure region to create resources in."
  type        = string
  default     = "eastus"
}
