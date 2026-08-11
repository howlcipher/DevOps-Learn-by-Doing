# Contributing

## Setup

```
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Checks before committing

```
flake8 src tests projects/api_platform/app projects/api_platform/tests
mypy
cd projects/api_platform && mypy app --strict && cd ../..
pytest
```

## Adding a detection, requirement, or recommendation rule

See "Adding a detection rule to ProjectAnalyzer" and "Adding a requirement or recommendation
rule" in `docs/development.md`.

## Adding a cloud provider

Implement the `CloudProvider` interface under `src/devops_learn/cloud/`, mapping every
existing `CloudConcept`. See `docs/cloud-model.md`.

## Adding a tool

All tool operations are simulated in V1. Implement the `Tool` interface in
`src/devops_learn/tools/`, declare accurate `risk_level`/`is_destructive` metadata, and
never bypass `ToolService.invoke`. See `docs/safety.md`.
