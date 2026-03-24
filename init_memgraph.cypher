// GMNAP V7 Academic Genealogy Graph Schema
// Implements mathematician-advisor relationships and lineage tracking
// IDEMPOTENT: safe to re-run on docker-compose restart

// Create constraints (idempotent — Memgraph ignores if exists)
CREATE CONSTRAINT ON (m:Mathematician) ASSERT m.global_id IS UNIQUE;
CREATE CONSTRAINT ON (i:Institution) ASSERT i.name IS UNIQUE;
CREATE CONSTRAINT ON (d:Degree) ASSERT d.id IS UNIQUE;

// Create indexes for performance
CREATE INDEX ON :Mathematician(canonical_latin);
CREATE INDEX ON :Mathematician(birth_year);
CREATE INDEX ON :Mathematician(death_year);
CREATE INDEX ON :Mathematician(region);
CREATE INDEX ON :Mathematician(msc_primary);
CREATE INDEX ON :Institution(country);
CREATE INDEX ON :Degree(year);
CREATE INDEX ON :Degree(type);

// Seed mathematician nodes (MERGE = idempotent)
MERGE (euler:Mathematician {global_id: "EULER_LEONHARD_1707_1783"})
SET euler.canonical_latin = "Euler, Leonhard",
    euler.canonical_native = "Euler, Leonhard",
    euler.birth_year = 1707,
    euler.death_year = 1783,
    euler.region = "A2",
    euler.confidence = 1.0,
    euler.msc_primary = "01-XX",
    euler.gdpr_data = false;

MERGE (gauss:Mathematician {global_id: "GAUSS_CARL_FRIEDRICH_1777_1855"})
SET gauss.canonical_latin = "Gauss, Carl Friedrich",
    gauss.canonical_native = "Gauß, Carl Friedrich",
    gauss.birth_year = 1777,
    gauss.death_year = 1855,
    gauss.region = "A2",
    gauss.confidence = 1.0,
    gauss.msc_primary = "11-XX",
    gauss.gdpr_data = false;

MERGE (riemann:Mathematician {global_id: "RIEMANN_BERNHARD_1826_1866"})
SET riemann.canonical_latin = "Riemann, Bernhard",
    riemann.canonical_native = "Riemann, Bernhard",
    riemann.birth_year = 1826,
    riemann.death_year = 1866,
    riemann.region = "A2",
    riemann.confidence = 1.0,
    riemann.msc_primary = "30-XX",
    riemann.gdpr_data = false;

// Seed institution nodes
MERGE (gottingen:Institution {name: "University of Göttingen"})
SET gottingen.country = "DE", gottingen.founded = 1737, gottingen.type = "university";

MERGE (basel:Institution {name: "University of Basel"})
SET basel.country = "CH", basel.founded = 1460, basel.type = "university";

// Seed degree node
MERGE (riemann_phd:Degree {id: "RIEMANN_PHD_1851"})
SET riemann_phd.title = "Grundlagen für eine allgemeine Theorie der Functionen einer veränderlichen complexen Größe",
    riemann_phd.year = 1851,
    riemann_phd.type = "PhD",
    riemann_phd.institution = "University of Göttingen";

// Advisor relationship (Gauss → Riemann)
MATCH (gauss:Mathematician {global_id: "GAUSS_CARL_FRIEDRICH_1777_1855"})
MATCH (riemann:Mathematician {global_id: "RIEMANN_BERNHARD_1826_1866"})
MERGE (riemann)-[:DOCTORAL_ADVISOR {relation_type: "doctoralAdvisor"}]->(gauss)
SET riemann.betweenness_score = 0.0;

// Degree relationship
MATCH (riemann:Mathematician {global_id: "RIEMANN_BERNHARD_1826_1866"})
MATCH (riemann_phd:Degree {id: "RIEMANN_PHD_1851"})
MERGE (riemann)-[:EARNED_DEGREE]->(riemann_phd);

MATCH (riemann_phd:Degree {id: "RIEMANN_PHD_1851"})
MATCH (gottingen:Institution {name: "University of Göttingen"})
MERGE (riemann_phd)-[:AWARDED_BY]->(gottingen);

// Centrality scores
MATCH (m:Mathematician) SET m.betweenness_score = coalesce(m.betweenness_score, 0.0);
MATCH (gauss:Mathematician {global_id: "GAUSS_CARL_FRIEDRICH_1777_1855"})
SET gauss.betweenness_score = 0.85;

// Graph metadata (MERGE = idempotent)
MERGE (meta:GraphMetadata {version: "v7.0"})
SET meta.last_updated = datetime(),
    meta.total_mathematicians = 3,
    meta.total_relationships = 1,
    meta.coherence_score = 1.0;

// Quality gate thresholds
MERGE (gates:QualityGates {version: "v7.0"})
SET gates.graph_coherence_min_quick = 0.85,
    gates.graph_coherence_min_full = 0.92,
    gates.graph_coherence_min_extreme = 0.97,
    gates.genealogy_edge_conflict_pct_max_quick = 2.0,
    gates.genealogy_edge_conflict_pct_max_full = 1.0,
    gates.genealogy_edge_conflict_pct_max_extreme = 0.0;

RETURN "GMNAP V7 graph schema initialized successfully" as status;
