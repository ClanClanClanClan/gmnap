-- Memgraph-compatible index creation
-- Note: Memgraph doesn't support IF NOT EXISTS or relationship indexes

-- Index on Mathematician nodes by global_id
CREATE INDEX ON :Mathematician(global_id);

-- Index on Mathematician nodes by canonical_latin
CREATE INDEX ON :Mathematician(canonical_latin);

-- Note: Memgraph doesn't support indexes on relationship properties
-- r.confidence filtering will be done at query time
