-- ============================================================
-- Reception Greeter – SQLite Schema
-- ============================================================

CREATE TABLE IF NOT EXISTS persons (
    person_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT    NOT NULL UNIQUE,
    role        TEXT    DEFAULT '',
    created_at  TEXT    NOT NULL DEFAULT (datetime('now')),
    updated_at  TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS embeddings (
    embedding_id INTEGER PRIMARY KEY AUTOINCREMENT,
    person_id    INTEGER NOT NULL,
    embedding    BLOB    NOT NULL,          -- numpy array serialised with tobytes()
    dim          INTEGER NOT NULL DEFAULT 512,
    quality_score REAL   DEFAULT 0.0,
    created_at   TEXT    NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (person_id) REFERENCES persons(person_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS events (
    event_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    person_id   INTEGER,                   -- NULL for unknown
    person_name TEXT    DEFAULT 'Unknown',
    event_type  TEXT    NOT NULL,           -- 'entry' or 'exit'
    confidence  REAL    DEFAULT 0.0,
    timestamp   TEXT    NOT NULL DEFAULT (datetime('now'))
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_embeddings_person ON embeddings(person_id);
CREATE INDEX IF NOT EXISTS idx_events_timestamp  ON events(timestamp);
CREATE INDEX IF NOT EXISTS idx_events_person     ON events(person_id);
