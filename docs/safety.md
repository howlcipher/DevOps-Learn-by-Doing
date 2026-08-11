# Safety: simulation vs. real, and controlled tool execution

## What is real in V1

- `ProjectAnalyzer` performs a real, read-only inspection of whatever repository path it is
  given (including this repo's own `projects/api_platform/`): real file presence checks, real
  regex scans of real file contents. It executes nothing.
- The demo FastAPI application (`projects/api_platform/`) is real, runnable code with real
  tests: `pip install -r requirements.txt && uvicorn app.main:app` actually runs it.
- The reference Dockerfile, Terraform configuration, Kubernetes manifest, and GitHub Actions
  workflow under `templates/` are real, valid configuration files, shown as examples.
- The platform's own persistence (SQLite), audit log, decisions, and experience tracking are
  real.

## What is simulated in V1

Every `Tool` implementation (`tools/*_tool.py`) is a `Simulated*Tool`: no `subprocess` calls, no
Docker daemon, no Terraform binary, no `kubectl`, no real Azure/AWS/GCP API calls, no network
access. This includes objectively low-risk operations like `git status`, kept simulated for one
unambiguous boundary rather than deciding operation by operation. Every simulated result's
summary text is marked "(simulated)". `devops-learn analyze <path>` runs in simulation mode with
zero cloud credentials; the one intentional deployment failure and its diagnosis
(`troubleshooting/service.py`) are also simulated, clearly narrated as such.

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
`OperatingMode`, including `AUTOPILOT`: mode only changes how much is explained around a call,
never whether approval is required (`docs/adr/0003-human-approval-gates.md`).

## Terraform plan risk

`validation/terraform_plan_analysis.analyze()` classifies a plan's `create`/`change`/`replace`/
`destroy` counts into a `RiskLevel`: any `destroy` is DESTRUCTIVE, any `replace` is HIGH, any
`change` is LOW, create-only is SAFE. `workflows/analyze_flow.py` simulates a resource
replacement whenever the chosen environment is `PRODUCTION`, so a production run visibly produces
a HIGH-risk plan.

## Destructive operations in V1's tool catalog

`terraform.destroy_approved_environment`, `kubernetes.delete_namespace`,
`cloud.remove_identity`, `cloud.delete_resource_group`. All require approval; none support a
dry-run bypass. `docker.remove_image` and `kubernetes.rollback` are HIGH risk (recoverable) and
do support a dry run that skips approval, since nothing real is destroyed either way in V1.

## Cost awareness

No cloud action in V1 can create a billable resource; `cloud.estimate_cost` deliberately never
returns a specific dollar figure, since V1 has no real pricing data to draw from.
Cost impact in a `Recommendation` (e.g. "lower likely cost than a managed cluster") is always
qualitative for the same reason.
