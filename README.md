# DevOps Learn by Doing

An AI-powered DevOps platform that evaluates what your project needs, explains the engineering
decisions, and builds the infrastructure with you.

Learn DevOps through the real systems being designed, deployed, and operated — not through
disconnected tutorials. The platform inspects a real project, tells you what it actually needs
versus what you only *want* for learning, asks you the handful of decisions that genuinely
matter, proposes and explains an architecture, generates and validates the implementation, and
performs it once you approve — all while keeping an append-only audit log and an evidence log of
what you were actually exposed to or did.

```text
Project -> Analysis -> Requirements -> Questions -> Recommendations -> Architecture
    -> Plan -> Validation -> Risk review -> Human approval -> Build -> Verify
    -> Troubleshoot -> Audit + Experience summary
```

## Status: V1 skeleton

V1 implements this full workflow end to end in **simulation mode**: real, deterministic project
analysis against any repository path (including the bundled Python FastAPI example), real
requirements/recommendation/architecture/plan logic, and simulated Docker/Terraform/Kubernetes/
cloud execution behind the same controlled-tool interface real execution will later use. Azure
is the only fully implemented cloud; AWS and GCP are honest extension points
(`ComingSoonError`, never fabricated parity). Python is the only fully supported language track
with a bundled example project; Go has detection but no bundled example yet. See
`docs/safety.md` for exactly what is real versus simulated.

## Install

```
pip install -e ".[dev]"
```

## Run

```
devops-learn analyze projects/api_platform --mode collaborate --learn-kubernetes
devops-learn review projects/api_platform
devops-learn history
devops-learn explain "Terraform state" --depth deep
```

`analyze` runs the full assess -> recommend -> build -> validate -> verify workflow.
`review` stops after assessment and produces a prioritized roadmap without building anything —
and can, correctly, tell you Kubernetes is not needed. `--mode` accepts `learn`, `collaborate`
(default), `autopilot`, or `review`; `--depth` accepts `brief`, `normal` (default), `learning`,
`deep`.

## Operating modes

| Mode | What it does |
|---|---|
| `learn` | Performs the work but explains extensively: what, why, alternatives, what to understand. |
| `collaborate` (default) | Handles routine implementation automatically; asks you to decide the recommendations and questions that materially affect architecture. |
| `autopilot` | Minimizes questions and narration; still requires human approval for HIGH/DESTRUCTIVE operations (Terraform apply, deletions, identity/secret changes) — never bypassed by mode. |
| `review` | Evaluates an existing project's DevOps maturity and produces a prioritized roadmap. Builds nothing. |

Explanation depth is a second, independent axis: "autopilot mode with deep explanations if I
inspect a decision" is representable, per `docs/adr/0002-explainable-ai-workflow.md`.

## Engineering needs vs. learning objectives

Every `Recommendation` tracks `engineering_need` and `learning_value` separately
(`docs/adr/0006-engineering-needs-vs-learning-objectives.md`). The platform will tell you
Kubernetes is unnecessary for a given workload even while proposing a Kubernetes-based
architecture *because you asked to learn it* — the two justifications are never merged into one
generic "reason."

## Safety

- The AI never gets unrestricted execution. Every capability is a `Tool`
  (`tools/base.py`) with declared risk level, dry-run support, and approval requirement;
  `ToolService` is the only caller of `Tool.execute` and enforces approval structurally.
  See `docs/adr/0004-controlled-tool-execution.md`.
- Decisions that recommend an architecture, and decisions that approve a specific destructive
  operation, are tracked separately (`docs/adr/0003-human-approval-gates.md`).
- Every decision-bearing structure (assessment, requirements, recommendations, architecture,
  plan, Terraform plan risk, diagnosis) is produced deterministically by this platform's own
  services; the LLM only ever produces freeform explanation text
  (`docs/adr/0008-structured-ai-output.md`). `MockLLMProvider` (used by default) proves every
  decision is correct with zero AI calls.

## Repository layout

- `src/devops_learn/` the platform: project analysis, requirements/questions/recommendations/
  architecture/planning services, controlled tools, cloud abstraction, explainability, audit,
  approvals, experience tracking, CLI.
- `projects/api_platform/` a real, runnable FastAPI application used as the example project for
  analysis — separate from the platform's own code.
- `templates/` reference Dockerfile, Terraform, Kubernetes, and GitHub Actions files.
- `docs/` architecture, cloud model, safety boundary, roadmap, and ADRs.
- `tests/` unit and workflow tests for the platform; `projects/api_platform/tests/` tests the
  demo app itself.

## Documentation

- `docs/architecture.md` service architecture, the core workflow, and the modular monolith
  rationale.
- `docs/cloud-model.md` the concept-first, multi-cloud abstraction.
- `docs/safety.md` simulation vs. real execution, approval gating, risk levels.
- `docs/roadmap.md` the next three milestones toward real execution.
- `docs/adr/` architecture decision records.

## Development

See `CONTRIBUTING.md` and `docs/development.md`.
