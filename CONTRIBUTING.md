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

Implement the `Tool` interface in `src/devops_learn/tools/`, declare accurate
`risk_level`/`is_destructive` metadata, and never bypass `ToolService.invoke`. Provide a
`Simulated*Tool` for tests/offline use and a `Real*Tool` that shells out to the actual binary
via an argument list (never `shell=True`), an explicit timeout, and
`tools/_subprocess_safety.py`'s redaction. See `docs/safety.md` and `docs/development.md`.

Any test needing real Azure credentials must be gated behind `RUN_AZURE_INTEGRATION_TESTS=1` so
normal CI never attempts to reach Azure.
