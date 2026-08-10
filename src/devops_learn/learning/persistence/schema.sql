-- V1 schema. One version, applied idempotently by migrations.py.
-- Timestamps are stored as ISO 8601 text; booleans as 0/1 integers.

CREATE TABLE IF NOT EXISTS schema_migrations (
    version INTEGER PRIMARY KEY,
    applied_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS learner_profiles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    display_name TEXT NOT NULL,
    cloud_provider TEXT NOT NULL,
    language_track TEXT NOT NULL,
    assistance_level TEXT NOT NULL,
    explanation_depth TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS learning_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    learner_id INTEGER NOT NULL REFERENCES learner_profiles(id),
    project_id TEXT NOT NULL,
    status TEXT NOT NULL,
    current_module_id TEXT,
    current_lesson_id TEXT,
    current_task_id TEXT,
    simulation_mode INTEGER NOT NULL,
    started_at TEXT NOT NULL,
    last_active_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_learning_sessions_learner
    ON learning_sessions(learner_id);

CREATE TABLE IF NOT EXISTS learning_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL REFERENCES learning_sessions(id),
    learner_id INTEGER NOT NULL REFERENCES learner_profiles(id),
    sequence_no INTEGER NOT NULL,
    event_type TEXT NOT NULL,
    occurred_at TEXT NOT NULL,
    module_id TEXT,
    lesson_id TEXT,
    task_id TEXT,
    payload_json TEXT NOT NULL,
    UNIQUE(session_id, sequence_no)
);

CREATE INDEX IF NOT EXISTS idx_learning_events_session
    ON learning_events(session_id);

CREATE TABLE IF NOT EXISTS competency_states (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    learner_id INTEGER NOT NULL REFERENCES learner_profiles(id),
    competency_code TEXT NOT NULL,
    state TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    evidence_event_id INTEGER REFERENCES learning_events(id),
    UNIQUE(learner_id, competency_code)
);

CREATE TABLE IF NOT EXISTS competency_transitions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    learner_id INTEGER NOT NULL REFERENCES learner_profiles(id),
    competency_code TEXT NOT NULL,
    from_state TEXT NOT NULL,
    to_state TEXT NOT NULL,
    triggering_event_id INTEGER NOT NULL REFERENCES learning_events(id),
    occurred_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_competency_transitions_learner
    ON competency_transitions(learner_id);

CREATE TABLE IF NOT EXISTS task_attempts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL REFERENCES learning_sessions(id),
    task_id TEXT NOT NULL,
    learner_id INTEGER NOT NULL REFERENCES learner_profiles(id),
    attempt_no INTEGER NOT NULL,
    started_at TEXT NOT NULL,
    completed_at TEXT,
    outcome TEXT,
    hints_used_count INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_task_attempts_session_task
    ON task_attempts(session_id, task_id);

CREATE TABLE IF NOT EXISTS hint_usages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_attempt_id INTEGER NOT NULL REFERENCES task_attempts(id),
    hint_level INTEGER NOT NULL,
    requested_at TEXT NOT NULL,
    event_id INTEGER REFERENCES learning_events(id)
);

CREATE TABLE IF NOT EXISTS artifacts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL REFERENCES learning_sessions(id),
    learner_id INTEGER NOT NULL REFERENCES learner_profiles(id),
    artifact_type TEXT NOT NULL,
    path_or_ref TEXT NOT NULL,
    created_at TEXT NOT NULL,
    event_id INTEGER REFERENCES learning_events(id)
);
