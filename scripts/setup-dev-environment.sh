#!/usr/bin/env bash
# Safe onboarding helper: inspect and explain prerequisites; it never installs
# packages, authenticates Azure, creates resources, or changes system settings.

set -euo pipefail

if [[ -r /etc/os-release ]]; then
    . /etc/os-release
    printf 'Detected platform: %s\n' "${PRETTY_NAME:-unknown Linux}"
else
    printf 'Detected platform: unknown\n'
fi

printf '\nThis helper makes no system or cloud changes.\n'
printf 'Install the project environment first: python -m venv .venv && .venv/bin/pip install -e ".[dev]"\n\n'

for command in git docker terraform az trivy conftest; do
    if command -v "$command" >/dev/null 2>&1; then
        printf '%-10s found: %s\n' "$command" "$(command -v "$command")"
    else
        printf '%-10s missing\n' "$command"
    fi
done

cat <<'EOF'

Supported installation references:
  Docker:    https://docs.docker.com/engine/install/
  Azure CLI: https://learn.microsoft.com/cli/azure/install-azure-cli-linux
  Trivy:     https://trivy.dev/latest/getting-started/installation/
  Conftest:  https://www.conftest.dev/install/

For this Ubuntu release, confirm that each vendor supports its package source
before modifying APT configuration. Do not pipe remote installation scripts to
the shell. After installing tools, run:

  .venv/bin/devops-learn doctor

Azure authentication is intentionally manual. When the doctor reports Azure
auth unavailable, run `az login` yourself and rerun the doctor.
EOF
