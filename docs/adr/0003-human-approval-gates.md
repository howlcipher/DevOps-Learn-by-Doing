# ADR 0003: Human approval gates

## Status

Accepted.

## Context

The platform can propose and, once approved, perform DevOps changes. Some of those changes are
inexpensive to undo (running a linter) and some are not (applying Terraform, deleting a resource
group). Approval must be structural, not a prompt-engineering convention the AI could skip.

## Decision

Two independent approval concerns exist:

1. **Tool-level approval** (`tools/approval.py`): every `ToolOperationSpec` carries
   `risk_level`, `requires_approval`, and `is_destructive`. `ToolService.invoke` is the only
   caller of `Tool.execute`, and it refuses to run an operation that requires approval without
   first getting a granted `ApprovalRecord` from an `ApprovalGate`. `OperatingMode.AUTOPILOT`
   changes how much is explained around a call, never whether approval is required.
2. **Decision-level approval** (`approvals/decision_service.py`): accepting, rejecting, or
   modifying a `Recommendation`, and answering a `ClarifyingQuestion`, are human decisions about
   architecture and tradeoffs, not about one tool call. These are recorded separately as
   `Decision` rows.

## Alternatives

- **One combined approval concept.** Rejected: conflates "should we use workload identity"
  (an architectural decision) with "should this specific `terraform apply` run now" (an
  operational gate); they have different audiences and different audit needs.

## Consequences

- No mode can bypass tool-level approval for a HIGH or DESTRUCTIVE risk operation; this is
  enforced in `ToolService`, not left to each workflow to remember.
- The audit log can distinguish "the user decided to use managed identity" from "the user
  approved this specific `terraform apply`."
