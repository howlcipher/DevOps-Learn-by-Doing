# Development

## Setup

```
python3 -m venv .venv
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
# Set your learner profile (stored in SQLite)
devops-learn profile --set docker=strong terraform=beginner --focus terraform

# Inspect a project and record goals
devops-learn init projects/api_platform

# Real local vertical slice: test -> lint -> docker build -> run -> verify
devops-learn local projects/api_platform

# Real Terraform vertical slice: fmt -> init -> validate -> plan -> risk analysis
# (plan requires Azure credentials -- az login, or ARM_CLIENT_ID/ARM_CLIENT_SECRET/
# ARM_TENANT_ID/ARM_SUBSCRIPTION_ID -- and fails cleanly, with an explanation, without them)
devops-learn terraform

# Simulate the full cloud workflow (no credentials, no cost)
devops-learn analyze projects/api_platform --mode collaborative --depth learning

# Review an existing project without building anything
devops-learn review projects/api_platform

# Explain a topic outside a session
devops-learn explain "Terraform state" --depth deep

# Show the audit history of the latest session
devops-learn history
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

Implement the `Tool` interface (`tools/base.py`), declare accurate
`risk_level`/`is_destructive`/`supports_dry_run` metadata, and never bypass
`ToolService.invoke`. `ToolOperationSpec.__post_init__` will reject an inconsistent DESTRUCTIVE
declaration at construction time.

Provide a `Simulated*Tool` for tests and environments where the real dependency is unavailable,
and a `Real*Tool` that shells out to the actual binary. See `tools/python_tool.py` and
`tools/docker_tool.py` for the base pattern, and `tools/terraform_tool.py` for a `Real*Tool`
that also needs an explicit subprocess timeout and output redaction — reuse
`tools/_subprocess_safety.py`'s `run_safely()`/`redact()` rather than calling `subprocess.run`
directly, so secret-shaped output can never accidentally reach a `ToolResult` unredacted.

Any future test that requires real Azure credentials must be gated behind
`RUN_AZURE_INTEGRATION_TESTS=1` (e.g.
`@pytest.mark.skipif(os.environ.get("RUN_AZURE_INTEGRATION_TESTS") != "1", reason="requires az
login")`), so ordinary CI and `pytest` runs never attempt to reach Azure. Nothing in the
platform needs this yet — it is the convention Milestone 3 (`docs/roadmap.md`) will use as soon
as real Azure calls exist.

## Adding a workflow command

CLI commands live in `cli/commands/*.py` and are registered in `cli/main.py`. They receive a
`Platform` from the composition root (`bootstrap.py`) and should remain thin: argument parsing
and a call to a workflow function in `workflows/`. Workflow functions depend only on the `Ui`
abstraction so they can be reused by a future web UI.

## Project layout

See the "Repository layout" section of README.md for the top-level map, and
docs/architecture.md for how the layers depend on each other.
