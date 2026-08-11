-- V1 schema. One version, applied idempotently by migrations.py.
-- Timestamps are stored as ISO 8601 text; booleans as 0/1 integers.

CREATE TABLE IF NOT EXISTS schema_migrations (
    version INTEGER PRIMARY KEY,
    applied_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS engagement_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_root TEXT NOT NULL,
    mode TEXT NOT NULL,
    explanation_depth TEXT NOT NULL,
    cloud TEXT NOT NULL,
    environment TEXT NOT NULL,
    cost_priority TEXT NOT NULL,
    simulation_mode INTEGER NOT NULL,
    started_at TEXT NOT NULL,
    completed_at TEXT
);

CREATE TABLE IF NOT EXISTS audit_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL REFERENCES engagement_sessions(id),
    sequence_no INTEGER NOT NULL,
    event_type TEXT NOT NULL,
    occurred_at TEXT NOT NULL,
    summary TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    UNIQUE(session_id, sequence_no)
);

CREATE INDEX IF NOT EXISTS idx_audit_events_session
    ON audit_events(session_id);

CREATE TABLE IF NOT EXISTS decisions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL REFERENCES engagement_sessions(id),
    subject_kind TEXT NOT NULL,
    subject_id TEXT NOT NULL,
    outcome TEXT NOT NULL,
    detail TEXT,
    decided_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_decisions_session
    ON decisions(session_id);

CREATE TABLE IF NOT EXISTS experience_entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL REFERENCES engagement_sessions(id),
    concept TEXT NOT NULL,
    item TEXT NOT NULL,
    state TEXT NOT NULL,
    occurred_at TEXT NOT NULL,
    UNIQUE(session_id, concept, item)
);

CREATE INDEX IF NOT EXISTS idx_experience_entries_session
    ON experience_entries(session_id);

CREATE TABLE IF NOT EXISTS artifacts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL REFERENCES engagement_sessions(id),
    artifact_type TEXT NOT NULL,
    path_or_ref TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_artifacts_session
    ON artifacts(session_id);

CREATE TABLE IF NOT EXISTS learner_profiles (
    id INTEGER PRIMARY KEY,
    proficiencies_json TEXT NOT NULL,
    focus_json TEXT NOT NULL
);
