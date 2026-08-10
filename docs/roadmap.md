# Roadmap beyond V1

V1 is a simulation-first skeleton (see docs/safety.md for exactly what is real vs. simulated).
The next three milestones, in order:

## Milestone 1: real local Python and Docker execution

Add `RealPythonTool` and `RealDockerTool` implementations of the existing `Tool` interface
(`tools/base.py`), invoking `pytest`/`flake8` and the local Docker daemon via a narrow,
allow-listed subprocess wrapper, gated by the same `ToolService.invoke` approval path already
in place. `SimulatedPythonTool`/`SimulatedDockerTool` stay available for tests and for
offline/no-Docker environments. No orchestrator or CLI changes should be required, since both
tools already sit behind `ToolService`.

## Milestone 2: real Terraform generation and validation, still simulated Azure

Add `RealTerraformTool.validate()`/`plan()` shelling out to a real `terraform` binary against
`templates/terraform/main.tf.reference` (or a learner-edited copy), with no `apply` and no
Azure credentials required, keeping `terraform apply`/`destroy` simulated until Milestone 3.
This directly extends `SimulatedTerraformTool.plan()`'s existing "derive the count from the
real config file" design, just backed by the real binary instead of a regex.

## Milestone 3: first real Azure deployment path, then Kubernetes fundamentals

Real `terraform apply` against a learner's own Azure subscription (behind the existing
approval gate, now backed by a real `CliApprovalGate` confirmation with actual cost
visibility), provisioning a resource group and container registry first. Kubernetes fundamentals
(real `kubectl` against a real or local cluster) follow once there is a real registry to pull
from, extending the concepts already introduced in the simulated `module_05_kubernetes_overview`
module into hands-on lessons with real Pods, Deployments, Services, and probes.

These three milestones are unchanged from the original plan; nothing built in V1 revealed a
reason to reorder them. If anything, the `Tool`/`ToolService` boundary and the
`is_available`/`ComingSoonError` pattern for cloud providers and language tracks turned out
cleaner than expected at isolating "real" from "simulated," which is why Milestone 1 and 2 are
scoped as narrowly as a single new file per tool.

## Further out (not yet milestoned)

Real AWS/GCP providers, a Go language track, richer troubleshooting scenarios beyond the one
container-won't-start case, a real Anthropic-backed tutoring session tested end to end (V1
tests `AnthropicProvider` only for import/credential behavior, not live calls), and rollback
scenarios affecting a real deployed environment.
