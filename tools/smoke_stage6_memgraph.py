from neo4j import GraphDatabase
import json, os, sys

URI = os.getenv("MG_URI", "bolt://localhost:7687")
AUTH = (os.getenv("MG_USER", ""), os.getenv("MG_PASSWORD", ""))


def mg_coherence(uri, auth, pairs):
    drv = GraphDatabase.driver(uri, auth=auth)
    with drv.session() as s:
        s.run(
            "CREATE CONSTRAINT mathematician_gid IF NOT EXISTS ON (m:Mathematician) ASSERT m.gid IS UNIQUE;"
        ).consume()
        s.run("MATCH (m:Mathematician) DETACH DELETE m;").consume()
        for a, b in pairs:
            s.run("MERGE (a:Mathematician {gid:$a})", a=a)
            s.run("MERGE (b:Mathematician {gid:$b})", b=b)
            s.run(
                "MATCH (a:Mathematician {gid:$a}),(b:Mathematician {gid:$b}) MERGE (a)-[:ADVISED]->(b)",
                a=a,
                b=b,
            )
        rec = s.run("""
            CALL betweenness_centrality.get()
            YIELD node, betweenness_centrality
            RETURN avg(betweenness_centrality) AS avg, max(betweenness_centrality) AS mx
        """).single()
    avg, mx = float(rec["avg"] or 0.0), float(rec["mx"] or 1.0)
    return 0.0 if mx <= 0 else max(0.0, min(1.0, avg / mx))


def bayes(score, sources, bw=0.6, aw=0.4, priors=None):
    priors = priors or {
        "Crossref": 0.9,
        "ORCID_ETD": 0.8,
        "OpenAlex": 0.85,
        "Wikidata_P184": 0.7,
    }
    alpha, beta = 1.0, 1.0
    for s in sorted(set(sources)):
        p = priors.get(s, 0.5)
        alpha += p
        beta += 1 - p
    auth = alpha / (alpha + beta)
    w = bw + aw or 1.0
    return {
        "betweenness": score,
        "authority_conf": auth,
        "stage6_score": (bw / w) * score + (aw / w) * auth,
    }


if __name__ == "__main__":
    pairs = [("A", "B"), ("B", "C"), ("B", "D")]
    s = mg_coherence(URI, AUTH, pairs)
    out = bayes(s, ["Crossref", "ORCID_ETD", "OpenAlex"])
    print(json.dumps(out, indent=2))
    sys.exit(0 if out["stage6_score"] >= 0.97 else 2)
