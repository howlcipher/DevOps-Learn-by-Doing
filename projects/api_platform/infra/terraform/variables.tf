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

variable "deploy_application" {
  description = "Set after the ACR image has been pushed. Bootstrap stays image-independent."
  type        = bool
  default     = false
}

variable "app_image" {
  description = "Immutable ACR image reference, including @sha256 digest, for the FastAPI app."
  type        = string
  default     = ""

  validation {
    condition     = !var.deploy_application || can(regex("@sha256:[0-9a-f]{64}$", var.app_image))
    error_message = "Application deployment requires an immutable image digest reference."
  }
}
