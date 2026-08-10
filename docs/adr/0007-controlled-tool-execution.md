# ADR 0007: Controlled tool execution

## Status

Accepted.

## Context

The AI tutor needs to trigger actions (build an image, run a Terraform plan, roll back a
deployment) without ever having unrestricted shell access, and destructive actions (a
Terraform destroy, a namespace deletion, an identity removal) must never execute purely
because a language model decided they were a good idea. The system needs this guarantee to
hold structurally, not just as a convention that every call site remembers to follow.

## Decision

All tool access goes through a fixed set of `Tool` implementations (tools/base.py), each
declaring `risk_level`, `supports_dry_run`, `requires_approval`, and `is_destructive` per
operation. `ToolOperationSpec.__post_init__` enforces two invariants at construction time: a
DESTRUCTIVE operation must require approval, and a DESTRUCTIVE operation must never support a
dry-run bypass. `ToolService.invoke` (tools/service.py) is the only entry point exposed to the
orchestrator or any AI-facing code; `Tool.execute` is never called from anywhere else. When an
operation requires approval and is not a dry run, `ToolService` blocks on `ApprovalGate.request`
before the tool's `execute` runs at all, and every tool's `execute` additionally asserts the
same precondition defensively. `CliApprovalGate` is the only gate wired into the real CLI;
`AutoApproveApprovalGate`/`AutoDenyApprovalGate` exist only for tests.

## Consequences

tests/tools/test_service.py proves the property directly with a spy `Tool` that records every
`execute` call: a denied destructive operation never reaches `execute` at all. The AI layer
(ai/provider.py) has no tool-invocation method of its own; it can only produce recommendations
and explanations, never call a tool directly, which keeps "should this destructive thing
happen" a human decision by construction rather than by prompt instruction. The cost is one
extra indirection (through `ToolService`) for every tool call, which is negligible.

## Alternatives considered

Trusting the LLM's own judgment about when to ask for confirmation was rejected outright: the
spec is explicit that safety must not depend solely on model behavior. A single global
"dangerous mode" flag that disables all approval prompts was considered for scripted demos and
rejected in favor of the narrower `AutoApproveApprovalGate`, which is reachable only from test
code, never from the CLI's composition root.
