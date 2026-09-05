-- Backfill chunks created before the full-text trigger existed.
-- The NULL predicate makes this a cheap no-op for a healthy database.
UPDATE rag_chunks
   SET content_tsv = to_tsvector('simple', COALESCE(content, ''))
 WHERE content_tsv IS NULL;
