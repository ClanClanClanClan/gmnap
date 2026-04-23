# MathLineage — Reviewer Walkthrough

A self-contained 10-minute tour of what the system does, written for a
reviewer who's never opened the repo before. If any step doesn't behave
as shown, see **Troubleshooting** at the bottom.

## 1. Setup

```bash
git clone <repo> gmnap && cd gmnap
make setup                 # pip install + compile fasttext CLI (~30s)
gmnap serve --port 8080    # start API + web UI
open http://localhost:8080 # (or point a browser at it)
```

`make setup` is the recommended path. For a minimal install without the
fasttext tiebreaker (rules-based region detection only), run
`pip install -r requirements.txt` instead; the CLI and API still work,
just with lower name-origin accuracy on hard cases.

---

## 2. CLI demo

The `gmnap` command exposes region detection, genealogy, and batch
processing. Five representative queries:

### Euler — Western Europe, with advisor chain

```bash
$ gmnap query "Euler, Leonhard"
CanonicalLatin: Euler, Leonhard
Region:         A2 (Western Europe)
Confidence:     0.95
BirthYear:      1707
Institution:    University of Basel
Advisors:       Bernoulli, Johann
```

### Kolmogorov — Cyrillic script, geo-via-suffix

```bash
$ gmnap query "Колмогоров, Андрей"
CanonicalLatin: Kolmogorov, Andrei
Region:         B1 (East Slavic)
Confidence:     0.98
DetectionMethod: signature_suffix (-ov)
```

### Tao — Chinese-heritage in the Anglosphere (diaspora conflict)

```bash
$ gmnap query "Tao, T."
CanonicalLatin: Tao, T.
GeoRegion:      A1  (Anglo-Sphere, via publication affiliation)
NameRegion:     E1  (Chinese, via surname)
Conflict:       diaspora
```

### Ramanujan — Dravidian, no advisor record

```bash
$ gmnap query "Ramanujan, Srinivasa"
CanonicalLatin: Ramanujan, Srinivasa
Region:         D2 (Dravidian)
Confidence:     0.91
```

### Lineage of Euler, depth 5

```bash
$ gmnap lineage --id "name:Euler, Leonhard" --depth 5
Euler, Leonhard
  → Bernoulli, Johann
    → Bernoulli, Jacob
      → Malebranche, Nicolas
      → Werenfels, Peter
```

---

## 3. Web UI demo

Open `http://localhost:8080`. Dark theme, no JS framework — plain
`app.js` + vendored `d3-v7` for the tree.

### 3.1 Landing page

![Landing](docs/screenshots/01_landing.png)

Type `/` anywhere to focus the search bar, or type a name and press
Enter.

### 3.2 Search results

Enter "Euler, Leonhard". The request goes through the full V7 pipeline
(region detection → authority enrichment → genealogy lookup) and returns
within a second in quick mode:

![Results](docs/screenshots/02_search_results.png)

### 3.3 Profile view

Click the result card to open the full profile: region badge,
confidence, birth year, institution, GlobalID, and advisors:

![Profile](docs/screenshots/03_profile_euler.png)

### 3.4 Genealogy tree

Scroll down — the **Advisor Tree** panel renders Euler's chain back
through the Bernoullis via d3-v7. Click any ancestor to navigate there.
The depth selector (3 / 5 / 8) re-queries the lineage endpoint:

![Tree](docs/screenshots/04_tree_euler.png)

### 3.5 Multi-advisor branching

Hilbert has two advisors (Lindemann and Weber). The tree splits cleanly:

![Hilbert tree](docs/screenshots/05_tree_hilbert.png)

### 3.6 Correction dialog

Every profile has a "Suggest Correction" button. Opens a modal with
categorized fields; HTML5 validation blocks empty submits:

![Correction](docs/screenshots/06_correction_dialog.png)

### 3.7 Mobile viewport (375×667)

Responsive layout collapses the search into the nav row and stacks the
feature cards:

![Mobile](docs/screenshots/07_mobile_viewport.png)

### 3.8 Graceful empty state

Unknown names return an empty state rather than crashing or hanging:

![Unknown](docs/screenshots/08_unknown_name.png)

---

## 4. API demo

Three endpoints, all rate-limited and hashcash-gated for the free tier
(18-bit SHA-256 PoW — spec §12). Paid tier uses Bearer token auth.

### Liveness

```bash
$ curl -fsS http://localhost:8080/healthz
{"status":"ok","version":"7.0","uptime_seconds":12.4}
```

### Name query (requires hashcash header)

```bash
# Generate a stamp — takes ~1 second on a modern CPU.
STAMP=$(python3 -c '
import hashlib, datetime
d = datetime.datetime.utcnow().strftime("%y%m%d")
i = 0
while True:
    s = f"1:18:{d}:gmnap-api::abc:{i:x}"
    h = hashlib.sha256(s.encode()).digest()
    z = 0
    for b in h:
        if b == 0: z += 8
        else:
            t = b
            while (t & 0x80) == 0: z += 1; t <<= 1
            break
    if z >= 18: print(s); break
    i += 1
')

curl -fsS \
  -H "X-Hashcash: $STAMP" \
  "http://localhost:8080/api/v1/query?name=Euler,%20Leonhard"
```

### Lineage

```bash
curl -fsS \
  -H "X-Hashcash: $STAMP" \
  "http://localhost:8080/api/v1/lineage/name:Euler,%20Leonhard?depth=5"
```

Response:

```json
{
  "root": "name:Euler, Leonhard",
  "depth": 5,
  "edges": [
    {"from": "Euler, Leonhard",   "to": "Bernoulli, Johann",  "relation": "doctoralAdvisor"},
    {"from": "Bernoulli, Johann", "to": "Bernoulli, Jacob",   "relation": "doctoralAdvisor"},
    {"from": "Bernoulli, Jacob",  "to": "Malebranche, Nicolas","relation": "doctoralAdvisor"},
    {"from": "Bernoulli, Jacob",  "to": "Werenfels, Peter",   "relation": "doctoralAdvisor"}
  ]
}
```

---

## 5. What this proves

- **Region detection is honest.** Every result returns a confidence and
  method. On the 523-entry adjudicated benchmark we have 100% leaf
  precision with 92% coverage — 28% honest R0 abstention rather than
  forcing wrong answers.
- **Genealogy is seeded + enriched.** 6,172 mathematicians with advisor
  chains, sourced from the MGP validation set plus Wikidata SPARQL
  (P184 doctoral advisor). Name matching is diacritic-insensitive and
  handles Dutch/German particles, hyphenated given names, and
  parenthetical aliases.
- **The web UI has been stress-tested.** `tools/browser_smoke.py`
  runs 29 adversarial scenarios against a real Chromium (XSS, Unicode,
  responsive, keyboard, rapid-fire, tree interaction, network
  resilience) with zero console errors.

---

## 6. Troubleshooting

### `fasttext: command not found` after `make setup`

The `install_fasttext.sh` script may have failed silently on macOS if
`build-essential`/Xcode CLT isn't present. Rules-only detection still
works (~92% leaf precision on European names, lower elsewhere) — ignore
the warning or fix the CLT install and re-run `make install-fasttext`.

### `/api/v1/lineage/...` returns 404

The endpoint first tries Memgraph, then local YAML pipeline output,
then the curated `data/genealogy_enrichment.json`. If all three miss,
you get 404. To check whether a name is known, inspect directly:

```bash
python3 -c "
from src.core.genealogy_lookup import GenealogyLookup
r = GenealogyLookup().lookup_by_name('Hilbert, David')
print(r or 'NOT FOUND')
"
```

### Docker compose fails to start Memgraph

Memgraph is optional — the API serves genealogy from the curated JSON
even without it. If `docker compose up` fails, run just the API:

```bash
docker run -d -p 8080:8080 -e OFFLINE=1 $(docker build -q .)
```

### Tree panel shows "Loading tree…" for several seconds

Expected. The browser computes an 18-bit SHA-256 hashcash stamp on
each call — takes ~1–5 s depending on the CPU and RNG luck. The free-
tier PoW is intentional (spec §12). Users with Bearer tokens skip it.
