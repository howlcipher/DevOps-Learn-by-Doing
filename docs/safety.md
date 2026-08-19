# Safety: simulation vs. real, and controlled tool execution

## What is real

- `ProjectAnalyzer` performs a real, read-only inspection of whatever repository path it is
  given (including this repo's own `projects/api_platform/`): real file presence checks, real
  regex scans of real file contents. It executes nothing.
- The demo FastAPI application (`projects/api_platform/`) and Go HTTP service
  (`projects/go_service/`) are real, runnable codebases with real tests and Dockerfiles.
- `devops-learn local <path>` runs real language toolchain commands (`pytest`, `flake8` for
  Python; `go test`, `go vet`, `go build`, `gofmt -l .` for Go) and real `docker build`, `docker run`,
  `docker logs`, and `docker stop` against the project you provide, and performs a real HTTP
  health check against the running container.
- `devops-learn terraform` runs real `terraform fmt`, `init`, `validate`, and `plan` (including
  `terraform show -json`) against `projects/api_platform/infra/terraform/`. It never applies or
  destroys anything. `init` downloads the `azurerm` provider plugin (network access, no Azure
  credentials required); `plan` requires Azure authentication (`az login`, or
  `ARM_CLIENT_ID`/`ARM_CLIENT_SECRET`/`ARM_TENANT_ID`/`ARM_SUBSCRIPTION_ID`) to build the
  provider client and fails cleanly, with an explanation, without it — see "Real Terraform
  execution" below.
- The platform's own persistence (SQLite), audit log, decisions, experience tracking, and learner
  profile are real.
- The reference Dockerfile, Terraform configuration, Kubernetes manifest, and GitHub Actions
  workflow under `templates/` are real, valid configuration files, shown as examples.
- `devops-learn security scan` is real, read-only local Trivy and Conftest execution when those
  binaries are available. It does not install tools, alter the working tree, apply Terraform, or
  contact Azure. Base refs are materialized with a temporary Git archive. Scanner evidence is
  structurally redacted before it reaches reports, console output, audit events, or explanations;
  raw scanner JSON is never persisted.

## What is simulated

- `devops-learn analyze` (without `--real-tools`) and `devops-learn review` use simulated
  Docker/Terraform/Kubernetes/cloud execution. No subprocess calls, no Docker daemon, no Terraform
  binary, no `kubectl`, no real Azure/AWS/GCP API calls, no outbound cloud provisioning. Every
  simulated result's summary text is marked "(simulated)".
- The intentional Kubernetes readiness-probe failure and diagnosis in `analyze` are simulated.

`SimulatedTerraformTool.plan()` derives its resource count by parsing
`templates/terraform/main.tf.reference`'s `resource` blocks rather than hardcoding a number, and
accepts a `simulate_replace` parameter so a `PRODUCTION` environment run demonstrates a
higher-risk plan (see `docs/adr/0004-controlled-tool-execution.md` and
`validation/terraform_plan_analysis.py`).

## Controlled tool execution

See docs/adr/0004-controlled-tool-execution.md. `LLMProvider` (`ai/provider.py`) has no method
that invokes a tool; it only produces freeform explanation text. `ToolService.invoke`
(`tools/service.py`) is the only entry point any workflow uses; `Tool.execute` is never called
from anywhere else.

Every tool operation declares `risk_level` (SAFE, LOW, HIGH, DESTRUCTIVE — see
`tools/approval.py`), `supports_dry_run`, `requires_approval`, and `is_destructive`. Two
invariants are enforced at construction time, not by convention:

- A DESTRUCTIVE operation must require approval.
- A DESTRUCTIVE operation must never support a dry-run bypass of that approval.

When an operation requires approval and is not a dry run, `ToolService` blocks on
`ApprovalGate.request` before the tool's `execute` runs at all; `CliApprovalGate` is the only
gate wired into the real CLI, prompting the human directly in the terminal.
`AutoApproveApprovalGate`/`AutoDenyApprovalGate` exist only for tests. This holds in every
`ExecutionMode`: mode only changes how much is explained or who performs the work, never whether
approval is required (`docs/adr/0003-human-approval-gates.md`).

## Real local execution safety

`devops-learn local` only runs local tools (`python`, `go`, and `docker`). It never provisions cloud
resources, applies Terraform, or modifies remote state. It:

- builds and runs a container on your local Docker daemon,
- maps a host port (default `8000`) to the container,
- stops the container at the end of the workflow,
- clearly labels every real result with `(real)`.

## Real Terraform execution

`devops-learn terraform`, `devops-learn deploy`, and `devops-learn destroy`
use `RealTerraformTool` (`tools/terraform_tool.py`). `devops-learn analyze
--real-tools` and `devops-learn local` still use `SimulatedTerraformTool` for
the `terraform` tool name. The standalone `terraform` command exposes only
`fmt`/`init`/`validate`/`plan`; `apply_approved_plan` and
`destroy_approved_environment` are real-only operations reached through the
explicit lifecycle commands. Apply accepts only a saved plan in `.devops_learn/plans` and
rechecks its digest, source identity, Terraform configuration digest, and
candidate context before invoking Terraform. Destroy requires an explicit
target environment and is followed by a read-only Azure resource-group check.
Neither operation can fall back to simulation; normal CI does not call either.

Terraform, Docker, and Azure CLI subprocess calls go through
`tools/_subprocess_safety.py::run_safely`, which sets an explicit timeout and
always redacts secret-shaped `KEY=value` text and truncates long output before
it reaches a `ToolResult`. `plan()`'s parsing of `terraform show -json` never extracts
raw resource attribute values (`before`/`after`) — only `{address, action}` per resource change
— which is the primary defense against leaking sensitive plan data; free-text redaction is
defense in depth on top of that.

A `terraform plan` failure due to missing Azure credentials is an expected, honest outcome on a
machine with no `az login`/`ARM_*` environment variables configured — `workflows/terraform_flow.py`
diagnoses it explicitly rather than treating it as a bug, and never fabricates a successful plan.

## Terraform plan risk

`validation/terraform_plan_analysis.analyze()` classifies a plan's `create`/`change`/`replace`/
`destroy` counts into a `RiskLevel`: any `destroy` is DESTRUCTIVE, any `replace` is HIGH, any
`change` is LOW, create-only is SAFE. `workflows/analyze_flow.py` simulates a resource
replacement whenever the chosen environment is `PRODUCTION`, so a production run visibly produces
a HIGH-risk plan.

## Destructive operations in the tool catalog

`terraform.destroy_approved_environment`, `kubernetes.delete_namespace`,
`cloud.remove_identity`, `cloud.delete_resource_group`. All require approval; none support a
dry-run bypass. `docker.remove_image` and `kubernetes.rollback` are HIGH risk (recoverable) and
do support a dry run that skips approval when the operation is simulated.

## Cost awareness

The real-only Azure lifecycle can create billable learning resources only after
explicit confirmations and tool-level approval. `cloud.estimate_cost` still
deliberately never returns a specific dollar figure, since it has no live
pricing data to draw from.
Cost impact in a `Recommendation` (e.g. "lower likely cost than a managed cluster") is always
qualitative for the same reason.

## Troubleshooting scenario safety and bounded fault injection

`devops-learn troubleshoot` creates realistic operational failure scenarios while strictly
preserving system integrity:

- **Bounded resource constraints**: Memory limit testing is confined to isolated container
  configurations (e.g. 6MB container limits) or deterministic simulations; it never starves or
  exhausts host machine memory.
- **Port isolation**: Port collisions use local ephemeral sockets/containers bound to loopback
  (`127.0.0.1`) and are guaranteed to close during teardown.
- **Harmless mock configurations**: Missing configuration scenarios test application fail-fast
  behavior using non-sensitive mock settings (e.g. `REQUIRED_CONFIG_KEY`), never real secrets.
- **Guaranteed teardown**: Every scenario runs cleanup inside a `finally` block to stop containers
  and release occupied resources regardless of whether the exercise succeeds, fails, or is aborted.
- **Honest capability reporting**: Scenarios clearly declare whether execution was `LIVE VERIFIED`
  or `SIMULATED / TESTED`. If Docker is absent, execution falls back cleanly to simulation.
