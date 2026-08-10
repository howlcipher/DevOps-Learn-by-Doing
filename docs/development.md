# Development

## Setup

```
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

`dev` includes `fastapi`/`uvicorn`/`httpx` so the demo app's own tests run through the same
`pytest` invocation as the platform's tests.

## Checks

```
flake8 src tests projects/api_platform/app projects/api_platform/tests
mypy
cd projects/api_platform && mypy app --strict && cd ../..
pytest
```

All four must pass before considering a change done; CI (`.github/workflows/ci.yml`) runs the
same four steps.

## Running it

```
devops-learn start
```

State persists to `~/.devops_learn/learning.db` by default; override with
`DEVOPS_LEARN_DB_PATH`. Set `ANTHROPIC_API_KEY` to use `AnthropicProvider` instead of
`MockLLMProvider`; simulation mode works identically either way.

## Adding curriculum content

Curriculum content lives under `src/devops_learn/curriculum/modules/` as plain Python builder
functions returning `domain.curriculum_models` dataclasses, assembled by
`curriculum/content_library.py`. See docs/learning-model.md for how `ContentBlock.min_depth`
and `always_include` interact with assistance level and explanation depth; a block that should
be exempt from depth filtering but still withheld at INDEPENDENT (like `WHAT`) should use the
default `min_depth` rather than `always_include=True`, which exempts a block from both axes.
`tests/curriculum/test_content_library_integrity.py` checks structural invariants (hint ladders
start at 1, check-question answer keys exist, every task declares a competency) automatically.

## Adding a cloud provider or language track

Implement `CloudProvider` (`cloud/base/provider.py`) or `LanguageTrack`
(`languages/base/language_track.py`), map every existing concept, and set
`is_available = True`. See docs/cloud-model.md.

## Adding a tool

All tool operations are simulated in V1 (docs/safety.md). Implement the `Tool` interface
(`tools/base.py`), declare accurate `risk_level`/`is_destructive`/`supports_dry_run` metadata,
and never bypass `ToolService.invoke`. `ToolOperationSpec.__post_init__` will reject an
inconsistent DESTRUCTIVE declaration at construction time.

## Project layout

See the "Repository layout" section of README.md for the top-level map, and
docs/architecture.md for how the layers depend on each other.
