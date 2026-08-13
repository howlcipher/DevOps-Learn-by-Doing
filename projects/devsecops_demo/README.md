# DevSecOps demo fixture

This project is an isolated, synthetic demonstration of change-aware security
gating. It contains no live credential, cloud state, or deployable service.

`baseline/` is the safe starting state. `proposed/` deliberately adds three
mistakes: a synthetic secret fixture, root container execution, and public SSH
ingress. `remediated/` removes those mistakes. Scan these directories only as
described in [docs/devsecops.md](../../docs/devsecops.md).

The value named `DEVSECOPS_DEMO_ONLY_NOT_A_CREDENTIAL` is deliberately fake
and must never be replaced with a usable credential.
