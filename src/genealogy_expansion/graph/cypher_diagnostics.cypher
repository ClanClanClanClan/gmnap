// Cycles
MATCH p=(m)-[:DOCTORAL_ADVISOR*1..20]->(m) RETURN COUNT(p) AS cycles;
// Missing dates
MATCH ()-[r:DOCTORAL_ADVISOR]->() WHERE r.degree_date IS NULL RETURN COUNT(r) AS missing_dates;
