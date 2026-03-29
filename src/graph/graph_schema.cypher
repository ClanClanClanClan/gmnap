// Minimal indexes for performance (Memgraph syntax)
CREATE INDEX ON :Mathematician(global_id);
CREATE INDEX ON :Mathematician(canonical_latin);
CREATE INDEX ON :Mathematician(region_code);
CREATE INDEX ON :Mathematician(birth_year);
