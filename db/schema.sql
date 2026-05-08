CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS facts (
    id            UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    project       TEXT         NOT NULL,
    developer_id  TEXT         NOT NULL,
    session_id    UUID         NULL,
    type          TEXT         NOT NULL,
    text          TEXT         NOT NULL,
    files         TEXT[]       NOT NULL DEFAULT '{}',
    embedding     vector(768)  NOT NULL,
    confidence    FLOAT        NOT NULL,
    status        TEXT         NOT NULL DEFAULT 'pending_review',
    superseded_by UUID         NULL,
    created_at    TIMESTAMPTZ  NOT NULL DEFAULT now(),
    refreshed_at  TIMESTAMPTZ  NOT NULL DEFAULT now(),
    stale_at      TIMESTAMPTZ  NULL
);

CREATE INDEX IF NOT EXISTS facts_embedding_idx
    ON facts USING hnsw (embedding vector_cosine_ops);
