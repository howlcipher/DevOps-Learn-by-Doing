from devops_learn.tools import _subprocess_safety


def test_redact_masks_secret_shaped_key_value_pairs() -> None:
    text = "Error: ARM_CLIENT_SECRET=abc123XYZ failed to authenticate"
    redacted = _subprocess_safety.redact(text)
    assert "abc123XYZ" not in redacted
    assert "ARM_CLIENT_SECRET=<redacted>" in redacted


def test_redact_leaves_non_secret_text_untouched() -> None:
    text = "Plan: 2 to add, 0 to change, 0 to destroy."
    assert _subprocess_safety.redact(text) == text


def test_truncate_caps_long_output_with_a_visible_marker() -> None:
    long_text = "x" * (_subprocess_safety.MAX_OUTPUT_CHARS + 500)
    result = _subprocess_safety._truncate(long_text)
    assert len(result) < len(long_text)
    assert "truncated" in result


def test_run_safely_returns_sanitized_result_on_success() -> None:
    result = _subprocess_safety.run_safely(
        ["python3", "-c", "print('hello')"], cwd=None, timeout=10
    )
    assert result.returncode == 0
    assert "hello" in result.stdout
    assert not result.timed_out


def test_run_safely_reports_timeout_without_hanging() -> None:
    result = _subprocess_safety.run_safely(
        ["python3", "-c", "import time; time.sleep(5)"], cwd=None, timeout=1
    )
    assert result.timed_out
    assert result.returncode != 0
    assert "timed out" in result.stderr.lower()


def test_run_safely_redacts_secret_shaped_stderr() -> None:
    result = _subprocess_safety.run_safely(
        [
            "python3",
            "-c",
            "import sys; sys.stderr.write('API_KEY=super-secret-value')",
        ],
        cwd=None,
        timeout=10,
    )
    assert "super-secret-value" not in result.stderr
    assert "API_KEY=<redacted>" in result.stderr
