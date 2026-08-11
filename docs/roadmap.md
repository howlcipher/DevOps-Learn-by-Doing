# Roadmap beyond V1

V1 is a simulation-first skeleton (see docs/safety.md for exactly what is real vs. simulated).
The next three milestones, in order:

## Milestone 1: real local execution

Add `RealPythonTool` and `RealDockerTool` implementations of the existing `Tool` interface
(`tools/base.py`): real `pytest`/`flake8` runs, real `docker build`/`run`/`logs` via a narrow,
allow-listed subprocess wrapper, gated by the same `ToolService.invoke` approval path already in
place. `SimulatedPythonTool`/`SimulatedDockerTool` stay available for tests and for
offline/no-Docker environments. No Azure credentials required. No workflow or CLI change should
be required, since both tools already sit behind `ToolService`.

## Milestone 2: real Terraform workflow

Add `RealTerraformTool` shelling out to a real `terraform` binary for `fmt`/`validate`/`plan`
against generated configuration, with structured parsing of `terraform show -json` feeding the
existing `validation/terraform_plan_analysis.analyze()` risk classifier unchanged. No `apply` and
no Azure credentials required yet; `apply_approved_plan`/`destroy_approved_environment` stay
simulated until Milestone 3. This directly extends the existing "derive real facts, never fake
them" pattern from `SimulatedTerraformTool.plan()`.

## Milestone 3: first Azure vertical slice

A small, real path: Python application -> Docker -> ACR -> Terraform -> minimal Azure
infrastructure -> deployment -> health verification, behind the existing approval gate (now
backed by `CliApprovalGate` confirming a real, non-simulated action). Provision a resource group
and container registry first. Introduce AKS/Kubernetes only after this first real cloud
execution path is reliable, per the product spec's explicit sequencing guidance — not because
Kubernetes is technically harder, but because a working real deployment path should exist before
adding cluster-level complexity on top of it.

## Further out (not yet milestoned)

Real AWS/GCP `CloudProvider` implementations, a bundled Go example project (detection already
exists), a richer `ProjectAnalyzer` (dependency graph analysis, actual secret-scanning
integration, Helm/Kubernetes-manifest-aware analysis), additional troubleshooting scenarios
beyond the one readiness-probe case, a real Anthropic-backed explanation path tested end to end
(V1 tests `AnthropicProvider` only for import/credential behavior, not live calls), and a web UI
reusing the existing `workflows`/`Ui` boundary.
