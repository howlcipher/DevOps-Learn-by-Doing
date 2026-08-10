# ADR 0003: Simulation first

## Status

Accepted.

## Context

The platform teaches Docker, Terraform, and Kubernetes, all of which can create real local
or cloud state, cost money, or damage a learner's system if invoked incorrectly. V1 needs a
first-run experience that requires zero setup: no Docker daemon, no Azure account, no local
kubectl context. It also needs to avoid ever presenting a fabricated result as if it were the
output of a real command.

## Decision

Every tool implementation in V1 (SimulatedPythonTool, SimulatedGitTool, SimulatedDockerTool,
SimulatedTerraformTool, SimulatedKubernetesTool, SimulatedCloudTool, SimulatedValidationTool)
is a simulation with no subprocess execution, no network calls, and no real Docker/cloud/
Kubernetes API access, including for objectively low-risk operations like `git status`. Every
simulated result's summary text is marked "(simulated)" so it is never mistaken for real
system state. `devops-learn start --simulation` is the only supported V1 entry point.

## Consequences

A learner can start the platform with nothing installed but Python, and the test suite runs
with no external services. The tradeoff is that V1 cannot yet teach the parts of DevOps that
only show up against a real system (real error messages, real timing, real flakiness); that
work is deliberately deferred to the milestones in docs/roadmap.md. The `Tool` ABC (tools/base.py)
is written so a `RealDockerTool` etc. can be added later as one new file per tool without
touching `ToolService` or any caller, so this boundary can move without a redesign.

## Alternatives considered

Executing real, but strictly read-only, commands (e.g. real `git status`, real `docker ps`)
was considered as a middle ground. It was rejected for V1 to keep one bright, unambiguous line
between simulated and real rather than deciding tool-by-tool and operation-by-operation, which
is easy to get subtly wrong under time pressure.
