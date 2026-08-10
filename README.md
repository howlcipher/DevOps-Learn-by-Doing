# DevOps Learn by Doing

Learn DevOps by actually doing DevOps, with an AI mentor that gradually gets out of your way.

This CLI walks a learner through building and operating a real, production style Python API
platform, from a local FastAPI app through Git, tests, Docker, GitHub Actions, Terraform,
Azure networking, Kubernetes, identity and secrets, observability, deployment, an intentional
failure, troubleshooting, rollback, and an architecture review. The AI explains, hints,
reviews, and steps back rather than doing the work for the learner. See
`docs/learning-model.md` for the full progression model.

## Status: V1 skeleton

V1 implements one project (`Production-Style API Platform`), one cloud path (Azure,
simulated), and one language path (Python). Kubernetes and Terraform curricula are
structural and simulated. AWS, GCP, and Go have clean extension points but no curricula yet.
Nothing in V1 requires cloud credentials or executes real docker/terraform/kubectl commands.
See `docs/safety.md` for exactly what is real versus simulated.

## Install

```
pip install -e ".[dev]"
```

## Run

```
devops-learn start --simulation
```

Other commands: `devops-learn resume`, `progress`, `projects`, `competencies`, `explain`.

## Repository layout

- `src/devops_learn/` the platform itself: curriculum engine, tutor orchestrator, domain
  model, competency tracking, simulated tools, cloud and language abstractions, CLI.
- `projects/api_platform/` the learner facing demo FastAPI application that the curriculum
  teaches against. This is a separate artifact from `src/devops_learn/projects/`, which is
  the platform's own project orchestration code, not application content.
- `templates/` reference Dockerfile, Terraform, Kubernetes, and GitHub Actions files used by
  hints and the simulated Terraform plan lesson.
- `docs/` architecture, learning model, cloud model, safety boundary, and ADRs.
- `tests/` unit and end to end tests for the platform; `projects/api_platform/tests/` tests
  the demo app itself.

## Documentation

- `docs/architecture.md` service architecture and the modular monolith rationale.
- `docs/learning-model.md` assistance levels, explanation depth, hints, competencies.
- `docs/cloud-model.md` the concept first, multi cloud abstraction.
- `docs/safety.md` simulation versus real execution, tool approval gating.
- `docs/development.md` local setup, checks, adding curriculum content.
- `docs/roadmap.md` planned milestones beyond V1.
- `docs/adr/` architecture decision records.

## Development

See `CONTRIBUTING.md` and `docs/development.md`.
