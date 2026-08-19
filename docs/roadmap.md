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

## Milestone 2: real Terraform workflow (done)

`RealTerraformTool` (`tools/terraform_tool.py`) shells out to a real
`terraform` binary for `fmt`/`init`/`validate`/`plan` against a real,
committed configuration (`projects/api_platform/infra/terraform/`), with
structured parsing of `terraform show -json` feeding the existing
`validation/terraform_plan_analysis.analyze()` risk classifier unchanged.
`devops-learn terraform` runs the full vertical slice (fmt -> init ->
validate -> plan -> risk analysis) and teaches Terraform state, provider,
and resource-address concepts just-in-time (`docs/terraform-state.md`). This
standalone command has no apply action; the separately approved lifecycle
commands introduced in Milestone 3 own real apply and destroy. `plan` requires
Azure authentication and fails cleanly, with an explanation, on a
machine without it — `init`/`validate`/`fmt` need no credentials.

## Milestone 3: first Azure vertical slice (implemented, awaiting live verification)

The real-only `deploy` workflow uses a two-stage path: bootstrap Resource Group,
ACR, Log Analytics, Container Apps Environment, managed identity and AcrPull;
then push a digest-pinned FastAPI image and apply the Container App plan.
It persists saved plans and candidate evidence, requires explicit confirmation
and tool approval, checks Azure independently, verifies `/health`, and offers
an approved `destroy` flow with an Azure cleanup check. Container Apps is the
right first fit for a small HTTP workload: it is managed and has much less
operational overhead than AKS. AKS remains deliberately out of scope.

This feature is not yet labelled live-verified: the current execution host has
no Azure CLI, Docker, Trivy, or Conftest, so a real Azure deployment and cleanup
remain an opt-in acceptance test.

## DevSecOps security control plane (done)

Trivy-backed filesystem/config/image evidence normalizes into scanner-independent
findings, compares a base Git state to the proposed state, and feeds inspectable
Conftest policy. The deterministic gate includes structural secret redaction,
audit/experience evidence, remediation classification, a report artifact, demo,
and PR CI. See `docs/devsecops.md`.

The gate is now bound to each deployment candidate before any real apply. Live
Azure verification remains the final opt-in acceptance step.

## Milestone 4: realistic troubleshooting with recovery verification (done)

`devops-learn troubleshoot` introduces structured operational incident recovery
scenarios (`port_conflict`, `missing_config`, `health_check_failure`, `resource_limit`)
with an explicit lifecycle:
SETUP -> INJECT -> OBSERVE -> EXPLAIN -> REMEDIATE -> VERIFY -> CLEANUP.
Observations are strictly separated from interpretations; progressive assistance
(Levels 0-4) guides the learner without leaking answers; recovery is deterministically
re-verified; and results are honestly distinguished between `LIVE VERIFIED` and
`SIMULATED / TESTED`.

## Further out (not yet milestoned)

- Real AWS/GCP `CloudProvider` implementations.
- A bundled Go example project (detection already exists).
- A richer `ProjectAnalyzer` (dependency graph analysis, actual secret-scanning
  integration, Helm/Kubernetes-manifest-aware analysis).
- A real Anthropic-backed explanation path tested end to end (V1 tests
  `AnthropicProvider` only for import/credential behavior, not live calls).
- A web UI reusing the existing `workflows`/`Ui` boundary.
- Optional interview-readiness and portfolio/evidence reports based on actual
  work performed.
