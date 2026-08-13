package main

# Conftest evaluates this deterministic policy over normalized, redacted JSON.
# Prefixes are parsed by security.policy; scanner severity alone never decides.

deny contains msg if {
  finding := input.findings[_]
  finding.change_status == "introduced"
  finding.severity == "critical"
  msg := sprintf("BLOCK: introduced critical finding %s (%s)", [finding.rule_id, finding.fingerprint])
}

deny contains msg if {
  finding := input.findings[_]
  finding.change_status == "introduced"
  finding.category == "secret"
  msg := sprintf("BLOCK: introduced secret finding %s (%s)", [finding.rule_id, finding.fingerprint])
}

deny contains msg if {
  finding := input.findings[_]
  finding.change_status == "introduced"
  finding.category == "network"
  contains(lower(finding.title), "public")
  contains(lower(finding.title), "ssh")
  msg := sprintf("BLOCK: introduced public administrative exposure %s", [finding.fingerprint])
}

deny contains msg if {
  finding := input.findings[_]
  finding.change_status == "introduced"
  finding.category == "network"
  contains(lower(finding.title), "public")
  contains(lower(finding.title), "rdp")
  msg := sprintf("BLOCK: introduced public administrative exposure %s", [finding.fingerprint])
}

deny contains msg if {
  finding := input.findings[_]
  finding.change_status == "introduced"
  finding.category == "kubernetes"
  contains(lower(finding.title), "privileged")
  msg := sprintf("BLOCK: introduced privileged Kubernetes workload %s", [finding.fingerprint])
}

warn contains msg if {
  finding := input.findings[_]
  finding.change_status == "introduced"
  finding.severity == "high"
  finding.category == "iac_misconfiguration"
  msg := sprintf("REQUIRE_APPROVAL: introduced high IaC finding %s (%s)", [finding.rule_id, finding.fingerprint])
}

warn contains msg if {
  finding := input.findings[_]
  finding.change_status == "introduced"
  finding.severity == "high"
  finding.category == "dependency"
  msg := sprintf("REQUIRE_APPROVAL: introduced high dependency finding %s (%s)", [finding.rule_id, finding.fingerprint])
}

warn contains msg if {
  finding := input.findings[_]
  finding.change_status == "introduced"
  finding.severity == "medium"
  msg := sprintf("WARN: introduced medium finding %s (%s)", [finding.rule_id, finding.fingerprint])
}

warn contains msg if {
  finding := input.findings[_]
  finding.change_status == "uncertain"
  finding.severity == "high"
  msg := sprintf("WARN: uncertain high-severity finding %s (%s)", [finding.rule_id, finding.fingerprint])
}

warn contains msg if {
  finding := input.findings[_]
  finding.change_status == "uncertain"
  finding.severity == "critical"
  msg := sprintf("WARN: uncertain high-severity finding %s (%s)", [finding.rule_id, finding.fingerprint])
}
