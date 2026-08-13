# infra/terraform

This is a real, valid Terraform configuration for a minimal Azure footprint:
a resource group, a container registry, and a Log Analytics workspace.

## Files in this directory

Terraform merges every `*.tf` file in a directory into a single
configuration. The split here (`providers.tf` / `variables.tf` / `main.tf` /
`outputs.tf`) is a naming convention for readability, not a module boundary
-- Terraform does not treat these as separate modules, and there is no
requirement to name files this way.

## What runs for real

`devops-learn terraform` runs real `fmt`, `init`, `validate`, and `plan`
against this directory via `RealTerraformTool`
(`src/devops_learn/tools/terraform_tool.py`). `init` downloads the `azurerm`
provider plugin (network access, no Azure credentials needed). `plan`
requires Azure authentication (`az login`, or `ARM_CLIENT_ID` /
`ARM_CLIENT_SECRET` / `ARM_TENANT_ID` / `ARM_SUBSCRIPTION_ID` environment
variables) to build the provider client -- without it, `plan` fails cleanly
and the workflow explains why rather than faking a result.

`devops-learn deploy` persists an approved plan before real apply; it never
accepts an arbitrary `terraform apply` command. `devops-learn destroy` is
separately destructive, requires explicit confirmation and tool approval, and
checks Azure after Terraform returns. These real-only operations are excluded
from CI and have not been exercised from this checkout without Azure credentials.

## Local state

Running `init`/`plan` here creates `.terraform/` and, if this configuration
is ever applied, `terraform.tfstate*` -- both are gitignored (see
`docs/terraform-state.md` for why state isn't committed).
`.terraform.lock.hcl` is committed on purpose: it pins the exact provider
version/hash so `init` is reproducible on every machine.
