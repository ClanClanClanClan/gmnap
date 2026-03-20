// GMNAP V7 Academic Genealogy Graph Schema
// Implements mathematician-advisor relationships and lineage tracking

// Create constraints and indexes for performance
CREATE CONSTRAINT ON (m:Mathematician) ASSERT m.global_id IS UNIQUE;
CREATE INDEX ON :Mathematician(canonical_latin);
CREATE INDEX ON :Mathematician(birth_year);
CREATE INDEX ON :Mathematician(death_year);
CREATE INDEX ON :Mathematician(region);
CREATE INDEX ON :Mathematician(msc_primary);

// Create constraint for institutions
CREATE CONSTRAINT ON (i:Institution) ASSERT i.name IS UNIQUE;
CREATE INDEX ON :Institution(country);

// Create constraint for degrees
CREATE CONSTRAINT ON (d:Degree) ASSERT d.id IS UNIQUE;
CREATE INDEX ON :Degree(year);
CREATE INDEX ON :Degree(type);

// Create sample mathematician nodes for testing
CREATE (euler:Mathematician {
    global_id: "EULER_LEONHARD_1707_1783",
    canonical_latin: "Euler, Leonhard",
    canonical_native: "Euler, Leonhard", 
    birth_year: 1707,
    death_year: 1783,
    region: "A2",
    confidence: 1.0,
    msc_primary: "01-XX",
    created_at: datetime(),
    gdpr_data: false
});

CREATE (gauss:Mathematician {
    global_id: "GAUSS_CARL_FRIEDRICH_1777_1855",
    canonical_latin: "Gauss, Carl Friedrich",
    canonical_native: "Gauß, Carl Friedrich",
    birth_year: 1777,
    death_year: 1855,
    region: "A2", 
    confidence: 1.0,
    msc_primary: "11-XX",
    created_at: datetime(),
    gdpr_data: false
});

CREATE (riemann:Mathematician {
    global_id: "RIEMANN_BERNHARD_1826_1866",
    canonical_latin: "Riemann, Bernhard",
    canonical_native: "Riemann, Bernhard",
    birth_year: 1826,
    death_year: 1866,
    region: "A2",
    confidence: 1.0,
    msc_primary: "30-XX",
    created_at: datetime(),
    gdpr_data: false
});

// Create institution nodes
CREATE (gottingen:Institution {
    name: "University of Göttingen",
    country: "DE",
    founded: 1737,
    type: "university"
});

CREATE (basel:Institution {
    name: "University of Basel",
    country: "CH", 
    founded: 1460,
    type: "university"
});

// Create degree relationships
CREATE (riemann_phd:Degree {
    id: "RIEMANN_PHD_1851",
    title: "Grundlagen für eine allgemeine Theorie der Functionen einer veränderlichen complexen Größe",
    year: 1851,
    type: "PhD",
    institution: "University of Göttingen"
});

// Create advisor relationships (V7 genealogy relations)
// Gauss advised Riemann (PhD 1851 at Göttingen)
MATCH (gauss:Mathematician {global_id: "GAUSS_CARL_FRIEDRICH_1777_1855"})
MATCH (riemann:Mathematician {global_id: "RIEMANN_BERNHARD_1826_1866"})
CREATE (riemann)-[:DOCTORAL_ADVISOR {
    relation_type: "doctoralAdvisor",
    confidence: 0.95,
    source: "MGP",
    year: 1851
}]->(gauss);

// Riemann earned his PhD
MATCH (riemann:Mathematician {global_id: "RIEMANN_BERNHARD_1826_1866"})
MATCH (riemann_phd:Degree {id: "RIEMANN_PHD_1851"})
CREATE (riemann)-[:EARNED_DEGREE {
    year: 1851,
    institution: "University of Göttingen"
}]->(riemann_phd);

// Degree awarded by Göttingen
MATCH (riemann_phd:Degree {id: "RIEMANN_PHD_1851"})
MATCH (gottingen:Institution {name: "University of Göttingen"})
CREATE (riemann_phd)-[:AWARDED_BY]->(gottingen);

// Create some sample betweenness centrality scores
// These would normally be calculated by the V7 pipeline Stage 6
MATCH (m:Mathematician)
SET m.betweenness_score = 0.0;

// Gauss has high centrality (many students)
MATCH (gauss:Mathematician {canonical_latin: "Gauss, Carl Friedrich"})
SET gauss.betweenness_score = 0.85;

// Create genealogy metadata
CREATE (meta:GraphMetadata {
    last_updated: datetime(),
    total_mathematicians: 3,
    total_relationships: 1,
    coherence_score: 1.0,
    version: "v7.0"
});

// Create query helpers for V7 pipeline
// Stage 6: Graph Consistency queries
CREATE (queries:QueryTemplates {
    find_cycles: "MATCH (a:Mathematician)-[:DOCTORAL_ADVISOR*1..3]->(b:Mathematician)-[:DOCTORAL_ADVISOR*1..3]->(a) RETURN a, b",
    betweenness_update: "CALL algo.betweenness.stream('Mathematician', 'DOCTORAL_ADVISOR') YIELD nodeId, centrality MATCH (m) WHERE id(m) = nodeId SET m.betweenness_score = centrality",
    coherence_check: "MATCH (m:Mathematician) WHERE m.betweenness_score >= 0.85 RETURN count(m) as high_centrality_count"
});

// V7 Stage 5: Collision Analytics support
// Create unique constraints to prevent duplicate GlobalIDs
// (Already done above with UNIQUE constraint)

// V7 Quality Gates support
CREATE (gates:QualityGates {
    graph_coherence_min_quick: 0.85,
    graph_coherence_min_full: 0.92,
    graph_coherence_min_extreme: 0.97,
    genealogy_edge_conflict_pct_max_quick: 2.0,
    genealogy_edge_conflict_pct_max_full: 1.0,
    genealogy_edge_conflict_pct_max_extreme: 0.0
});

RETURN "GMNAP V7 graph schema initialized successfully" as status;