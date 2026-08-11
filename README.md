# DevOps Learn by Doing

An AI-native DevOps learning and engineering environment. It performs real
project work while deliberately teaching the concepts you need to understand.

The goal is not to make you stop using AI, and it is not to let AI do
everything blindly. The goal is **AI-assisted DevOps mastery**: you and the AI
do real engineering work together, and the platform explains exactly enough for
you to direct, review, troubleshoot, validate, and improve what the AI produces.

```text
Project -> Analysis -> Requirements -> Questions -> Recommendations -> Architecture
    -> Plan -> Validation -> Risk review -> Human approval -> Build -> Verify
    -> Troubleshoot -> Audit + Experience summary
```

## What works

- **Real project analysis** against any repository path, including the bundled
  `projects/api_platform` FastAPI app.
- **Learner skill profile**: declare what you already know and what you want to
  learn so explanations target your actual gaps.
- **Project intake** (`devops-learn init`) inspects a project and asks only the
  questions that cannot be inferred safely.
- **Real local execution** (`devops-learn local`) runs actual `pytest`, `flake8`,
  `docker build`, `docker run`, and HTTP health checks against the project.
- **Simulated cloud/Terraform/Kubernetes** execution for safe learning without
  credentials or cost (`devops-learn analyze` without `--real-tools`).
- **Controlled tool execution**: every capability is a `Tool` with declared
  risk level, dry-run support, and human approval; `ToolService` is the only
  caller of `Tool.execute`.
- **Competency evidence tracking**: records what you were exposed to, practiced,
  or demonstrated, not fabricated certification.

See `docs/safety.md` for exactly what is real versus simulated.

## Install

```
pip install -e ".[dev]"
```

## Quick start

```
# Set up a learner profile (optional but recommended)
devops-learn profile --set docker=strong terraform=beginner azure=developing \
                     --focus terraform --focus azure

# Inspect a project and record your goals
devops-learn init projects/api_platform

# Run a real local vertical slice: test -> lint -> docker build -> run -> verify
devops-learn local projects/api_platform

# Simulate the full cloud workflow (no credentials, no cost)
devops-learn analyze projects/api_platform --mode collaborative --depth learning

# Review an existing project's maturity without building anything
devops-learn review projects/api_platform

# Explain a topic outside a session
devops-learn explain "Terraform state" --depth deep
```

## Execution modes

Execution mode controls **who performs the work**. Explanation depth controls
**how much detail** is provided. They are independent axes.

| Mode | What it does |
|---|---|
| `observe` | AI analyzes and explains; no changes are made. |
| `guided` | AI explains the next step; you perform meaningful actions. |
| `collaborative` (default) | AI generates and performs substantial work while involving you in important decisions. |
| `ai_executed` | AI performs approved work and narrates what, why, expected result, actual result, risks, and rollback. |
| `autonomous` | AI may execute a sequence of previously authorized safe operations. Destructive/costly/production-impacting actions still require approval. |

## Explanation depth

| Depth | What it provides |
|---|---|
| `brief` | Action summary only. |
| `normal` (default) | Action, why, decision, alternatives, tradeoff. |
| `learning` | Adds "what you should understand" with conceptual context. |
| `deep` | Full conceptual background, risk, validation, and next steps. |

## AI-assisted DevOps mastery

The platform teaches in context: when Terraform or Azure concepts appear, it
explains them at the depth your learner profile says you need. Competency is
measured by understanding and judgment — recognizing a dangerous Terraform plan,
explaining why state matters, diagnosing a failing container — not by how many
commands you manually typed. See `docs/learning-model.md`.

## Engineering needs vs. learning objectives

Every `Recommendation` tracks `engineering_need` and `learning_value` separately
(`docs/adr/0006-engineering-needs-vs-learning-objectives.md`). The platform will
tell you Kubernetes is unnecessary for a given workload even while proposing a
Kubernetes-based architecture *because you asked to learn it* — the two
justifications are never merged into one generic "reason."

## Safety

- The AI never gets unrestricted execution. Every capability is a `Tool`
  (`tools/base.py`) with declared risk level, dry-run support, and approval
  requirement; `ToolService` is the only caller of `Tool.execute` and enforces
  approval structurally. See `docs/adr/0004-controlled-tool-execution.md`.
- Decisions that recommend an architecture, and decisions that approve a
  specific destructive operation, are tracked separately
  (`docs/adr/0003-human-approval-gates.md`).
- Every decision-bearing structure (assessment, requirements, recommendations,
  architecture, plan, Terraform plan risk, diagnosis) is produced
deterministically by this platform's own services; the LLM only ever produces
freeform explanation text (`docs/adr/0008-structured-ai-output.md`).
  `MockLLMProvider` (used by default) proves every decision is correct with zero
  AI calls.

## Repository layout

- `src/devops_learn/` the platform: project analysis,
  requirements/questions/recommendations/architecture/planning services,
  controlled tools, cloud abstraction, explainability, audit, approvals,
  experience tracking, learner profile, CLI.
- `projects/api_platform/` a real, runnable FastAPI application used as the
  example project for analysis — separate from the platform's own code.
- `templates/` reference Dockerfile, Terraform, Kubernetes, and GitHub Actions files.
- `docs/` architecture, learning model, cloud model, safety boundary, roadmap,
  and ADRs.
- `tests/` unit and workflow tests for the platform; `projects/api_platform/tests/`
  tests the demo app itself.

## Documentation

- `docs/learning-model.md` the AI-assisted mastery philosophy, learner profile,
  and just-in-time learning approach.
- `docs/architecture.md` service architecture, the core workflow, and the
  modular monolith rationale.
- `docs/cloud-model.md` the concept-first, multi-cloud abstraction.
- `docs/safety.md` simulation vs. real execution, approval gating, risk levels.
- `docs/roadmap.md` the next milestones.
- `docs/adr/` architecture decision records.

## Development

See `CONTRIBUTING.md` and `docs/development.md`.
