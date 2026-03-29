
-- Example analytics that could be expanded for collision scoring
WITH dup AS (
  SELECT CanonicalLatin, BirthYear, COUNT(*) AS c
  FROM entries
  GROUP BY 1,2 HAVING COUNT(*) > 1
)
SELECT * FROM dup ORDER BY c DESC, CanonicalLatin;
