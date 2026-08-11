# Roadmap

## Current state

The platform is an AI-assisted DevOps mastery environment, not a static course.
It performs real project work while teaching concepts in context.

Completed in the latest iteration:

- Learner skill profile and knowledge-gap model (`docs/learning-model.md`).
- Execution modes separated from explanation depth.
- Project intake command (`devops-learn init`).
- Real local Python and Docker tool implementations behind the existing `Tool`
  interface, with simulated versions preserved.
- Local vertical slice command (`devops-learn local`): inspect -> test -> lint ->
  Docker build -> run -> HTTP verify -> logs -> stop.
- Optional failure injection in `local` mode for practicing container log
  diagnosis.

## Milestone 1: real local execution (done)

`RealPythonTool` and `RealDockerTool` implement the `Tool` interface: real
`pytest`/`flake8` runs and real `docker build`/`run`/`logs`/`stop` via a narrow,
allow-listed subprocess wrapper, gated by `ToolService.invoke`.
`SimulatedPythonTool`/`SimulatedDockerTool` remain available for tests and for
offline/no-Docker environments. The `devops-learn local` command runs the full
local vertical slice end to end and teaches Docker concepts in context.

## Milestone 2: real Terraform workflow

Add `RealTerraformTool` shelling out to a real `terraform` binary for
`fmt`/`validate`/`plan` against generated configuration, with structured
parsing of `terraform show -json` feeding the existing
`validation/terraform_plan_analysis.analyze()` risk classifier unchanged. No
`apply` and no Azure credentials required yet;
`apply_approved_plan`/`destroy_approved_environment` stay simulated until
Milestone 3.

## Milestone 3: first Azure vertical slice

A small, real path: Python application -> Docker -> ACR -> Terraform -> minimal
Azure infrastructure -> deployment -> health verification, behind the existing
approval gate confirming a real, non-simulated action. Provision a resource
group and container registry first. Introduce AKS/Kubernetes only after this
first real cloud execution path is reliable — not because Kubernetes is
technically harder, but because a working real deployment path should exist
before adding cluster-level complexity on top of it.

## Further out (not yet milestoned)

- Real AWS/GCP `CloudProvider` implementations.
- A bundled Go example project (detection already exists).
- A richer `ProjectAnalyzer` (dependency graph analysis, actual secret-scanning
  integration, Helm/Kubernetes-manifest-aware analysis).
- More troubleshooting scenarios beyond the readiness-probe and container-exit
  cases.
- A real Anthropic-backed explanation path tested end to end (V1 tests
  `AnthropicProvider` only for import/credential behavior, not live calls).
- A web UI reusing the existing `workflows`/`Ui` boundary.
- Optional interview-readiness and portfolio/evidence reports based on actual
  work performed.
