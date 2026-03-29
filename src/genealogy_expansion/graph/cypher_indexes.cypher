CREATE INDEX mathematician_by_id IF NOT EXISTS FOR (m:Mathematician) ON (m.global_id);
CREATE INDEX mathematician_by_name IF NOT EXISTS FOR (m:Mathematician) ON (m.canonical_latin);
CREATE INDEX advisor_confidence IF NOT EXISTS FOR ()-[r:DOCTORAL_ADVISOR]-() ON (r.confidence);
