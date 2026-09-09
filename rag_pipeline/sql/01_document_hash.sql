CREATE EXTENSION IF NOT EXISTS pgcrypto;

ALTER TABLE rag_documents
    ADD COLUMN IF NOT EXISTS content_sha256 CHAR(64);

-- Existing rows are considered unchanged after the migration.  New indexing
-- stores the same normalized text in raw_content before calculating the hash.
UPDATE rag_documents
   SET content_sha256 = encode(digest(raw_content, 'sha256'), 'hex')
 WHERE content_sha256 IS NULL
   AND raw_content IS NOT NULL;
