# DevOps-Learn-by-Doing

## Product

This is an AI-assisted DevOps mastery platform, not an automation tool and
not an anti-AI exercise. The goal is real engineering work performed
together with AI in a way that deliberately closes the user's knowledge
gaps. AI automation and learner understanding are two separate dimensions:
running a command for the user is not the same as the user understanding
why it ran or what it did. See `docs/learning-model.md`. Never equate manual
typing with expertise, and never let AI execution stand in for competency
evidence — evidence lives in `ExperienceTracker`/`ExperienceState`
(`experience/tracker.py`, `domain/enums.py`).

## Architecture

Modular monolith (`docs/architecture.md`, `docs/adr/0001`). `bootstrap.py`
is the single composition root — all concrete implementations are wired
there via constructor injection, never a service locator. `domain/` depends
on nothing; `tools/`/`cloud/`/`ai/` depend only on `domain/`;
`workflows/`/`bootstrap.py` depend on everything; `cli/` depends only on
`bootstrap.py`/`workflows/`/`domain/`. Preserve this layering unless there
is a strong reason to change it.

Every capability the platform can execute is a `Tool` (`tools/base.py`).
`ToolService.invoke` (`tools/service.py`) is the only caller of
`Tool.execute` anywhere in the codebase — this is what makes "destructive
operations require human approval" structural rather than a convention any
one caller has to remember. Never bypass `ToolService` for convenience, and
never call `Tool.execute` directly outside it.

LLMs explain and reason; deterministic code decides. `LLMProvider`
(`ai/provider.py`) has no method that invokes a tool or makes a decision —
it only produces freeform explanation text. Recommendations, risk
classification, and plans are typed dataclasses produced by deterministic
services (`docs/adr/0008-structured-ai-output.md`), never freeform LLM
output parsed at runtime.

## Safety

- Never fabricate successful execution. Every real result is explicitly
  labeled `(real)`/`(real, failed)`; every simulated result says
  `(simulated)`. See `docs/safety.md` for the current real-vs-simulated
  boundary — keep it accurate as implementation changes.
- `ToolOperationSpec` (`tools/base.py`) enforces at construction time that a
  `RiskLevel.DESTRUCTIVE` operation must require approval and must never
  support a dry-run bypass of that approval. Do not work around this.
- `ApprovalGate`/`CliApprovalGate` (`tools/approval.py`) is the only path to
  approving a HIGH/DESTRUCTIVE operation; `AutoApproveApprovalGate`/
  `AutoDenyApprovalGate` exist only for tests, never for the real CLI.
- Never commit credentials, Terraform state, or `.env` files. Real
  subprocess-backed tools must redact secret-shaped output before it lands
  in a `ToolResult` (see `tools/_subprocess_safety.py`) and must set an
  explicit timeout on every subprocess call.
- Never expose unrestricted arbitrary shell execution through a `Tool`. Real
  tools shell out to a narrow, allow-listed set of operations via argument
  arrays (never `shell=True`) — see `tools/docker_tool.py`,
  `tools/python_tool.py`, `tools/terraform_tool.py`.

## Product direction

- Azure first; Terraform depth before AWS/GCP breadth (`docs/cloud-model.md`).
- Do not add Kubernetes/AKS until a real cloud deployment path is proven
  reliable without it — not because Kubernetes is technically harder, but
  because cluster-level complexity should sit on top of a working real
  deployment path, not substitute for one (`docs/roadmap.md`).
- Prefer understandable learning infrastructure over enterprise complexity —
  no module registries, landing zones, Terragrunt, or multi-subscription
  setups unless a milestone genuinely requires them.
- See `docs/roadmap.md` for current milestone status before proposing new
  scope.

## Quality

Before considering any change complete, all of the following must pass:

```
pytest
flake8 src tests projects/api_platform/app projects/api_platform/tests
mypy
cd projects/api_platform && mypy app --strict
```

Update `docs/roadmap.md`/`docs/safety.md` when implementation reality
changes — this repo's credibility depends on never claiming more than what
is genuinely implemented (e.g. do not describe real Azure execution as
working unless it has actually been verified against a real subscription).

Do not put task-specific notes, implementation plans, or milestone journals
in this file — it is for durable project knowledge only.
