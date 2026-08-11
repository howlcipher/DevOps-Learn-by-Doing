# Learning model

## Goal: AI-assisted DevOps mastery

The platform does not try to make the learner independent from AI, and it does
not let AI do everything blindly. The objective is to understand DevOps well
enough to confidently **direct, review, troubleshoot, validate, and improve**
AI-assisted infrastructure and operations. AI remains part of the workflow
even after mastery.

Competency means:

- knowing what is being built and why
- understanding how the pieces interact
- knowing what can fail
- being able to diagnose failures
- being able to evaluate AI-generated solutions
- being able to make architectural decisions
- knowing how to validate changes safely
- knowing how to recover when something goes wrong

It does **not** mean memorizing syntax or typing every command by hand.

## Two independent axes

### Execution mode: who performs the work

| Mode | What it means |
|---|---|
| `observe` | AI analyzes and explains; no changes are made. |
| `guided` | AI explains the next step; the human performs meaningful actions. |
| `collaborative` | AI generates and performs substantial work while involving the human in important decisions. |
| `ai_executed` | AI performs approved work and narrates what, why, expected result, actual result, risks, and rollback. |
| `autonomous` | AI may execute a sequence of previously authorized safe operations toward an approved objective. Destructive/costly/production-impacting actions still require approval. |

### Explanation depth: how much detail is provided

| Depth | What it means |
|---|---|
| `brief` | One-line action summary. |
| `normal` | Action, why, decision, alternatives, tradeoff. |
| `learning` | Adds "what you should understand" with conceptual context. |
| `deep` | Full conceptual background, risk, validation, and next steps. |

The two axes are independent. "`ai_executed` mode with `deep` explanations" and
"`collaborative` mode with `brief` explanations" are both valid.

## Learner skill profile

The platform stores a sparse learner profile: a map of `CompetencyArea` to
`ProficiencyLevel` and a set of `learning_focus` areas. If an area is missing, it
is assumed to be `beginner`.

Competency areas include: `docker`, `git`, `ci_cd`, `azure`, `terraform`,
`kubernetes`, `networking`, `python`, `go`, `cloud_architecture`, `security`,
`secrets`, `observability`.

Proficiency levels: `beginner`, `developing`, `working`, `strong`, `expert`.

The profile is used to spend explanation time where gaps exist. If a learner is
`strong` in Docker, Docker explanations are kept brief; if they are `beginner`
in Terraform, Terraform concepts are explained more deeply as they appear.

## Competency evidence

`ExperienceState` tracks evidence of understanding, not certification:

- `not_started`
- `introduced`
- `guided`
- `practiced`
- `demonstrated`

Advancement is based on meaningful evidence: reasoning through a scenario,
answering an architectural question, diagnosing a failure, reviewing an
AI-generated plan, or making a meaningful change. Memorized syntax or
autocomplete do not determine competency.

## Just-in-time learning

Concepts are introduced at the moment they are needed, not as a front-loaded
course. When the platform generates or runs Terraform, it explains:

- **WHAT** the resource is
- **WHY** the architecture needs it
- **HOW** the syntax works
- **CONTEXT** how this relates to the cloud provider
- **RISK** what could go wrong
- **VALIDATION** how to verify it
- **NEXT** how it connects to the following infrastructure

The depth of each of those points depends on the learner profile and the
current explanation depth.

## AI-generated work must be reviewable

Before significant execution the platform shows:

- what was generated
- the assumptions behind it
- the risks
- the validation it ran
- the plan or diff
- what approval is required

This teaches the skill of supervising AI-generated engineering, which is
central to the product.
