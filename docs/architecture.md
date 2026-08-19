# Architecture

## Shape

A modular monolith (ADR 0001), not a multi-agent swarm. One process, one composition root
(`bootstrap.py`), constructor injection throughout, no service locator.

```text
workflows/analyze_flow.py   sequences the services below for one engagement; no business logic
    |
    +-- analysis.ProjectAnalyzer        inspects a real repository -> ProjectAssessment
    +-- requirements.RequirementsService  ProjectAssessment -> DetectedRequirement
    +-- questions.QuestionService       decides which ClarifyingQuestion is material
    +-- recommendations.RecommendationService  requirements + decisions -> Recommendation
    +-- architecture.ArchitectureService  recommendations -> ArchitectureProposal (concept-first)
    +-- planning.PlanningService        proposal -> ImplementationPlan of Tool operations
    +-- validation.terraform_plan_analysis  pure risk classification of a Terraform plan
    +-- security.normalize/change_analysis/policy  normalized security evidence and gate
    +-- troubleshooting.TroubleshootingService  gathers evidence, then diagnoses
    +-- tools.ToolService               the only entry point into any Tool
    +-- explanations.ExplanationService  renders Explanation/LearningMoment by mode+depth
    +-- experience.ExperienceTracker    the evidence log (not a mastery model)
    +-- audit.AuditService              the append-only audit_events journal
    +-- approvals.DecisionService       records human decisions on questions/recommendations
    +-- learning.SessionService         EngagementSession lifecycle
    +-- learning.LearnerProfileService  stores skill profile and learning focus
    +-- workflows.local_flow            real local vertical slice (test -> Docker -> verify)
    +-- workflows.security_flow         Trivy -> base comparison -> Conftest policy -> gate
    +-- ai.LLMProvider                  MockLLMProvider (default) or AnthropicProvider
```

`run_analysis` (`workflows/analyze_flow.py`) depends only on an abstract `Ui`
(`workflows/ui.py`): `present`, `ask_choice`, `confirm`. `cli/terminal_ui.py` is the only `Ui`
implementation wired into the real CLI; a future web UI would add its own without changing any
service or workflow.

## Core workflow

```text
Project -> ProjectAnalyzer -> RequirementsService -> QuestionService (human decisions)
    -> RecommendationService (human decisions) -> ArchitectureService -> PlanningService
    -> ValidationService/ToolService (tests, lint, terraform validate/plan)
    -> risk analysis -> human approval -> ToolService (build/apply/deploy)
    -> health verification -> TroubleshootingService (on failure) -> AuditService/ExperienceTracker
```

`ExecutionMode.OBSERVE` stops after requirements/architecture and produces a prioritized roadmap;
nothing is built. The other modes (`GUIDED`, `COLLABORATIVE`, `AI_EXECUTED`, `AUTONOMOUS`) run
the full workflow, differing in how much the human performs versus how much the AI performs —
never in whether a HIGH/DESTRUCTIVE tool operation requires approval
(`docs/adr/0003-human-approval-gates.md`).

`workflows/local_flow.py` implements a separate real local vertical slice (`devops-learn local`):
inspect -> test -> lint -> Docker build -> run -> HTTP verify -> logs -> stop. It uses real
`python` and `docker` tools while keeping cloud/Terraform/Kubernetes simulated.

`workflows/security_flow.py` is the pre-deployment security stage. It invokes
Trivy through `SecurityScannerTool`, normalizes redacted findings, compares an
explicit Git base through a temporary archive, invokes Conftest through
`PolicyTool`, records audit and experience evidence, and emits a sanitized
report. Operational tool risk remains separate from the deployment decision.
See `docs/devsecops.md`.

## Layers

```text
domain/           plain dataclasses and enums; no behavior, no I/O
analysis/         ProjectAnalyzer: real filesystem/text inspection, no execution
requirements/, questions/, recommendations/, architecture/, planning/, validation/
                  deterministic decision services; see docs/adr/0008-structured-ai-output.md
tools/            the controlled tool interface + simulated and real implementations
troubleshooting/  gathers ToolResult-derived evidence, then diagnoses
ai/               LLMProvider abstraction + Mock/Anthropic implementations (explanation only)
cloud/            concept-first extension points (Azure implemented; AWS/GCP stubs)
audit/, approvals/, experience/   cross-cutting recording services
learning/         session lifecycle + sqlite repositories
workflows/        the Ui abstraction and the flow that sequences everything above
cli/              argparse commands + TerminalUi; imports workflows/services, nothing imports it
bootstrap.py      the composition root
```

Dependencies point one direction: `domain` depends on nothing else in the package; `tools`,
`cloud`, `ai` depend only on `domain`; `analysis`/`requirements`/`questions`/`recommendations`/
`architecture`/`planning`/`validation`/`troubleshooting`/`explanations`/`experience`/`audit`/
`approvals` depend on `domain` and, where relevant, `tools`/`cloud`; `learning` depends on
`domain`; `workflows` and `bootstrap` depend on everything; `cli` depends only on `bootstrap`,
`workflows`, and `domain`.

## Project analysis

`ProjectAnalyzer.analyze(root)` is heuristic and conservative on purpose: file presence checks
(`Dockerfile`, `*.tf`, `.github/workflows/*.yml`) and a handful of regex scans (framework
imports, `/health` routes, `os.environ`/`os.getenv` calls, hardcoded-credential shapes). It never
executes anything and never calls an LLM. Anything it cannot observe directly is recorded as an
`Assumption` with a confidence, never asserted as fact.

## Explainability

See `docs/adr/0002-explainable-ai-workflow.md`. Not every action gets a full
ACTION/WHY/DECISION/ALTERNATIVES/TRADEOFF/WHAT_TO_UNDERSTAND/RESULT rendering; trivial actions
supply only `action` and render as one line.

## Troubleshooting

See `troubleshooting/service.py` and `workflows/troubleshooting_flow.py`. Evidence gathering
always precedes diagnosis: the platform never hands an LLM an unstructured failure description.
The troubleshooting engine manages bounded operational recovery scenarios (`port_conflict`,
`missing_config`, `health_check_failure`, `resource_limit`) with an explicit lifecycle:
`SETUP -> INJECT -> OBSERVE -> EXPLAIN -> REMEDIATE -> VERIFY -> CLEANUP`.
Observations (facts) are separated from interpretations (hypotheses), progressive hints (0-4)
guide the learner without preempting discovery, and recovery is deterministically re-verified
before completion.

## Persistence

stdlib `sqlite3`, no ORM. All SQL is confined to `learning/persistence/repositories/`; every
other layer works with plain dataclasses. See `learning/persistence/schema.sql` for
`engagement_sessions`, `audit_events`, `decisions`, `experience_entries`, and `artifacts`.

## Safety

`ToolService.invoke` is the only way to call a `Tool`; destructive operations require human
approval enforced structurally, not by convention. See docs/safety.md.

## Where to look for more detail

- docs/cloud-model.md: the concept-first multi-cloud abstraction.
- docs/safety.md: simulation vs. real execution, approval gating, risk levels.
- docs/adr/: the reasoning behind each of the above.
