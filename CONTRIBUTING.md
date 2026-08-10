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

## Adding curriculum content

Curriculum content lives under `src/devops_learn/curriculum/modules/` as plain Python
builder functions returning domain dataclasses. See `docs/learning-model.md` for the
content authoring model (assistance level and explanation depth composition).

## Adding a cloud or language track

Implement the `CloudProvider` or `LanguageTrack` interface under `src/devops_learn/cloud/`
or `src/devops_learn/languages/`. Do not implement a full curriculum for a new provider
until the concept model in `docs/cloud-model.md` covers it.

## Adding a tool

All tool operations are simulated in V1. Implement the `Tool` interface in
`src/devops_learn/tools/`, declare accurate `risk_level`/`is_destructive` metadata, and
never bypass `ToolService.invoke`. See `docs/safety.md`.
