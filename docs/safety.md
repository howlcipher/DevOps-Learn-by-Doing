# Safety: simulation vs. real, and controlled tool execution

## What is real in V1

- The demo FastAPI application (`projects/api_platform/`) is real, runnable code with real
  tests. You can `pip install -r requirements.txt && uvicorn app.main:app` and it actually runs.
- The reference Dockerfile, Terraform configuration, Kubernetes manifest, and GitHub Actions
  workflow under `templates/` are real, valid configuration files, shown as examples.
- The platform's own persistence (SQLite), competency tracking, and learning history are real.

## What is simulated in V1

Every `Tool` implementation (`tools/*_tool.py`) is a `Simulated*Tool`: no `subprocess` calls,
no Docker daemon, no Terraform binary, no `kubectl`, no real Azure/AWS/GCP API calls, no
network access. This includes objectively low-risk operations like `git status`, kept
simulated for one unambiguous boundary rather than deciding operation by operation (see
docs/adr/0003-simulation-first.md). Every simulated result's summary text is marked
"(simulated)". `devops-learn start` runs in simulation mode with zero cloud credentials.

`SimulatedTerraformTool.plan()` derives its resource count by parsing
`templates/terraform/main.tf.reference`'s `resource` blocks rather than hardcoding a number, so
the output stays connected to a real (if unapplied) configuration.

## Controlled tool execution

See docs/adr/0007-controlled-tool-execution.md. The AI layer (`ai/provider.py`) has no method
that invokes a tool; it can only produce recommendations and explanations. `ToolService.invoke`
(`tools/service.py`) is the only entry point exposed to the orchestrator; `Tool.execute` is
never called from anywhere else.

Every tool operation declares `risk_level` (SAFE, LOW, HIGH, DESTRUCTIVE), `supports_dry_run`,
`requires_approval`, and `is_destructive`. Two invariants are enforced at construction time,
not by convention:

- A DESTRUCTIVE operation must require approval.
- A DESTRUCTIVE operation must never support a dry-run bypass of that approval.

When an operation requires approval and is not a dry run, `ToolService` blocks on
`ApprovalGate.request` before the tool's `execute` runs at all; `CliApprovalGate` is the only
gate wired into the real CLI, prompting the learner directly in the terminal.
`AutoApproveApprovalGate`/`AutoDenyApprovalGate` exist only for tests.

## Destructive operations in V1's tool catalog

`terraform.destroy_approved_environment`, `kubernetes.delete_namespace`,
`cloud.remove_identity`, `cloud.delete_resource_group`. All require approval; none support a
dry-run bypass. `docker.remove_image` and `kubernetes.rollback` are HIGH risk (recoverable) and
do support a dry run that skips approval, since nothing real is destroyed either way in V1.

## Cost awareness

No cloud action in V1 can create a billable resource; `cloud.estimate_cost` deliberately never
returns a specific dollar figure, since V1 has no real pricing data to draw from.
