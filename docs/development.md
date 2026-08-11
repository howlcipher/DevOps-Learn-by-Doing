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
devops-learn analyze projects/api_platform --mode collaborate --learn-kubernetes
devops-learn review projects/api_platform
devops-learn history
devops-learn explain "Terraform state" --depth deep
```

State persists to `~/.devops_learn/learning.db` by default; override with
`DEVOPS_LEARN_DB_PATH`. Set `ANTHROPIC_API_KEY` to use `AnthropicProvider` instead of
`MockLLMProvider`; simulation mode works identically either way, since `LLMProvider` only ever
produces freeform explanation text (docs/adr/0008-structured-ai-output.md).

## Adding a detection rule to ProjectAnalyzer

`analysis/project_analyzer.py` is a single class with small private helper methods per
category (`_detect_framework`, `_has_ci_workflows`, `_detect_test_status`, ...). Add a new regex
or file check there, and add both a positive and a negative case to
`tests/analysis/test_project_analyzer.py` using `tmp_path`.

## Adding a requirement or recommendation rule

`requirements/service.py` and `recommendations/service.py` are both table-driven `if` chains
keyed off `ProjectAssessment`/`DetectedRequirement.id`. Add a new branch, then add a test in
`tests/requirements/test_service.py` or `tests/recommendations/test_service.py` asserting the
new id appears (or is absent) under the right conditions. If the recommendation could ever be
justified purely by a learning objective rather than the workload's actual needs, set
`engineering_need` and `learning_value` independently — see
docs/adr/0006-engineering-needs-vs-learning-objectives.md.

## Adding a cloud provider

Implement `CloudProvider` (`cloud/base/provider.py`), map every existing `CloudConcept`, and set
`is_available = True`. See docs/cloud-model.md.

## Adding a tool

All tool operations are simulated in V1 (docs/safety.md). Implement the `Tool` interface
(`tools/base.py`), declare accurate `risk_level`/`is_destructive`/`supports_dry_run` metadata,
and never bypass `ToolService.invoke`. `ToolOperationSpec.__post_init__` will reject an
inconsistent DESTRUCTIVE declaration at construction time.

## Project layout

See the "Repository layout" section of README.md for the top-level map, and
docs/architecture.md for how the layers depend on each other.
