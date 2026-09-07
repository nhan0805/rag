CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS rag_documents (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_path  TEXT NOT NULL UNIQUE,
    raw_content  TEXT,
    doc_type     VARCHAR(30),
    title        TEXT,
    doc_date     DATE,
    area         VARCHAR(100),
    status       VARCHAR(40),
    tags         TEXT[],
    description  TEXT,
    summary      TEXT,
    metadata     JSONB,
    created_at   TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at   TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Classification is optional for the original fixture. When supplied, the
-- retrieval/cache scope can enforce it without changing existing documents.
ALTER TABLE rag_documents
    ADD COLUMN IF NOT EXISTS classification_id TEXT;

CREATE TABLE IF NOT EXISTS rag_chunks (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id  UUID NOT NULL REFERENCES rag_documents(id) ON DELETE CASCADE,
    chunk_index  INT NOT NULL,
    content      TEXT NOT NULL,
    token_count  INT NOT NULL,
    metadata     JSONB,
    content_tsv  TSVECTOR,
    UNIQUE (document_id, chunk_index)
);

CREATE TABLE IF NOT EXISTS rag_embeddings (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    chunk_id    UUID NOT NULL REFERENCES rag_chunks(id) ON DELETE CASCADE,
    embedding   VECTOR({{EMBEDDING_DIM}}) NOT NULL,
    model       VARCHAR(80) NOT NULL,
    UNIQUE (chunk_id)
);

CREATE INDEX IF NOT EXISTS rag_chunks_document_idx
    ON rag_chunks (document_id, chunk_index);

CREATE INDEX IF NOT EXISTS rag_chunks_content_tsv_idx
    ON rag_chunks USING gin (content_tsv);

CREATE INDEX IF NOT EXISTS rag_embeddings_embedding_hnsw_idx
    ON rag_embeddings USING hnsw (embedding vector_cosine_ops);

CREATE OR REPLACE FUNCTION rag_set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS rag_documents_updated_at ON rag_documents;
CREATE TRIGGER rag_documents_updated_at
BEFORE UPDATE ON rag_documents
FOR EACH ROW EXECUTE FUNCTION rag_set_updated_at();

CREATE OR REPLACE FUNCTION rag_chunks_tsv_update()
RETURNS TRIGGER AS $$
BEGIN
    NEW.content_tsv = to_tsvector('simple', COALESCE(NEW.content, ''));
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS rag_chunks_tsv_update ON rag_chunks;
CREATE TRIGGER rag_chunks_tsv_update
BEFORE INSERT OR UPDATE OF content ON rag_chunks
FOR EACH ROW EXECUTE FUNCTION rag_chunks_tsv_update();

UPDATE rag_chunks
SET content = content
WHERE content_tsv IS NULL;

CREATE TABLE IF NOT EXISTS rag_query_cache (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    question       TEXT NOT NULL,
    question_vec   VECTOR({{EMBEDDING_DIM}}) NOT NULL,
    scope_key      CHAR(64) NOT NULL,
    answer         TEXT NOT NULL,
    sources        JSONB NOT NULL DEFAULT '[]'::jsonb,
    document_ids   UUID[] NOT NULL DEFAULT '{}'::uuid[],
    hit_count      INT NOT NULL DEFAULT 0,
    created_at     TIMESTAMP NOT NULL DEFAULT NOW(),
    expires_at     TIMESTAMP
);

CREATE INDEX IF NOT EXISTS rag_query_cache_scope_idx
    ON rag_query_cache (scope_key);
CREATE INDEX IF NOT EXISTS rag_query_cache_documents_idx
    ON rag_query_cache USING gin (document_ids);

CREATE TABLE IF NOT EXISTS rag_conversation_turns (
    id              BIGSERIAL PRIMARY KEY,
    conversation_id TEXT NOT NULL,
    user_id         TEXT NOT NULL,
    question        TEXT NOT NULL,
    answer          TEXT NOT NULL,
    created_at      TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS rag_conversation_owner_idx
    ON rag_conversation_turns (conversation_id, user_id, created_at DESC, id DESC);

CREATE OR REPLACE FUNCTION rag_invalidate_cache_on_document_delete()
RETURNS TRIGGER AS $$
BEGIN
    DELETE FROM rag_query_cache WHERE OLD.id = ANY(document_ids);
    RETURN OLD;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS rag_documents_cache_invalidation ON rag_documents;
CREATE TRIGGER rag_documents_cache_invalidation
AFTER DELETE ON rag_documents
FOR EACH ROW EXECUTE FUNCTION rag_invalidate_cache_on_document_delete();
