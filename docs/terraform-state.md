# Terraform state

`devops-learn terraform` (`workflows/terraform_flow.py`) surfaces a subset of
these concepts just-in-time, right before the command that makes them
relevant -- not as a front-loaded course. This doc is the fuller reference
those in-flow moments link back to.

## Desired state vs. actual infrastructure vs. Terraform state

Three things, easy to conflate:

- **Desired state**: what your `.tf` files declare should exist.
- **Actual infrastructure**: what really exists in Azure right now.
- **Terraform state**: Terraform's own record of what it believes exists,
  stored in `terraform.tfstate`. This is neither of the other two -- it's
  Terraform's memory, built from the last successful apply (or import).

`terraform plan` diffs desired state against Terraform's state file, then
confirms that against the real provider API. All three can disagree with
each other; when state and actual infrastructure disagree, that's drift.

## Provider

A provider is the plugin Terraform uses to talk to a specific platform --
`azurerm` for Azure. `terraform init` downloads it. Every resource type's
prefix (`azurerm_resource_group`, `azurerm_container_registry`) names the
provider that owns it.

## Resource address

A resource's address (e.g. `azurerm_resource_group.main`) combines its type
and a local name. Terraform uses addresses as keys into the state file and to
build the dependency graph between resources -- e.g. the container registry
in `main.tf` implicitly depends on the resource group because it references
`azurerm_resource_group.main.name`.

## Dependencies

Terraform builds a dependency graph from resource references (not file
order) and applies/destroys in graph order: dependencies before dependents on
create, dependents before dependencies on destroy.

## Drift

Drift is when the real infrastructure no longer matches what Terraform's
state file says it should be -- usually because someone changed a resource
outside Terraform (Azure Portal, `az` CLI, another tool). `terraform plan`
detects drift by refreshing state against the real provider before diffing,
so a plan can show changes even though nothing in your `.tf` files changed.

## Local vs. remote state, and locking

This milestone only uses **local state**: `terraform.tfstate` sits in the
working directory. That's fine solo, but two people (or two CI runs) applying
concurrently against local state can corrupt it. **Remote state** (e.g. an
Azure Storage blob) centralizes the file and typically adds **locking**, so
only one `apply` can run against a given state file at a time. Remote state
and locking are out of scope for this milestone; see `docs/roadmap.md`.

## State sensitivity

State can contain resource attribute values, including ones marked sensitive
by a provider (connection strings, generated passwords, keys). This is why
`terraform.tfstate*` is gitignored (see `.gitignore`) -- committing it would
commit those values in plaintext into version control history.

## Why deleting state does not delete infrastructure

`terraform.tfstate` is Terraform's memory, not a control plane. Deleting it
does not touch Azure at all -- it only makes Terraform forget every resource
it was tracking. Run `terraform plan` afterward and every real resource would
show up as something Terraform wants to *create*, because as far as
Terraform now knows, nothing exists yet. The real resources are still there,
now unmanaged and orphaned from Terraform's perspective.

## Why hand-editing state is dangerous

State's internal schema is version-specific and includes fields (resource
dependency ordering, provider-specific metadata) that aren't meant to be
edited by hand. A manual edit that doesn't match reality can cause Terraform
to plan a destructive "fix" -- e.g. destroying and recreating a resource
Terraform now believes doesn't match its record, even though the real
resource is fine. Use `terraform state` subcommands (`mv`, `rm`, `import`)
instead of editing the file directly; even those require care and are
DESTRUCTIVE-adjacent operations in this platform's risk model (see
`docs/safety.md`).

## Real vs. simulated in this platform

`devops-learn terraform` runs real `fmt`/`init`/`validate`/`plan` against
`projects/api_platform/infra/terraform/` and never applies or destroys.
`apply_approved_plan`/`destroy_approved_environment` -- and therefore any
real state file this platform would ever write -- stay simulated until
Milestone 3. See `docs/safety.md` and `docs/roadmap.md`.
