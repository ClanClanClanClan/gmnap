# Authority Source Access Guide
*Last Updated: 2026-03-16*

This document explains how to obtain API access for all 14 authority sources used by GMNAP v7, organised by tier.

---

## Tier 0 -- Free, No Authentication

These sources work out of the box. No setup required.

### OpenAlex
- **URL**: https://api.openalex.org
- **Licence**: CC0
- **Daily quota**: 864,000 requests (10/sec)
- **Setup**: None. Set `GMNAP_EMAIL` env var for polite pool (higher priority).
- **What it provides**: OpenAlex author ID, ORCID, display name, works count, institution, country, h-index
- **Adapter**: `src/authority/openalex_adapter.py`

### Crossref
- **URL**: https://api.crossref.org
- **Licence**: CC0
- **Daily quota**: 4,300,000 requests (50/sec with polite pool)
- **Setup**: None. Set `GMNAP_EMAIL` for polite pool (higher rate limits).
- **What it provides**: DOIs, publication count, co-authors, subjects, venues
- **Adapter**: `src/authority/crossref_adapter.py`

### ORCID Public API
- **URL**: https://pub.orcid.org/v3.0
- **Licence**: CC0
- **Daily quota**: 100,000 requests
- **Setup**: None for public search. The expanded-search endpoint requires no auth.
- **What it provides**: ORCID iD, institution names
- **Adapter**: `src/authority/orcid_etd_adapter.py`

### Crossref Thesis Search
- **URL**: https://api.crossref.org/works (filtered by type=dissertation)
- **Licence**: CC0
- **Daily quota**: 100,000 requests
- **Setup**: Same as Crossref above.
- **What it provides**: Thesis DOI, degree date with precision, institution name
- **Adapter**: `src/authority/crossref_thesis_adapter.py`

---

## Tier 1 -- Free, Rate-Limited

These sources are free but have lower rate limits. They run in Full and Extreme modes when `OFFLINE=0`.

### Wikidata (P184 Doctoral Advisor)
- **URL**: https://query.wikidata.org/sparql
- **Licence**: CC0
- **Daily quota**: Bulk dump available; SPARQL has soft limits
- **Setup**: None. Uses SPARQL endpoint directly.
- **Rate limits**: Wikidata asks for max 1 req/sec for SPARQL. The adapter uses rps=2 with burst=2.
- **What it provides**: Doctoral advisor names (P184), doctoral students (P185), ORCID (P496), birth/death years (P569/P570)
- **Adapter**: `src/authority/wikidata_p184_adapter.py`
- **Note**: For bulk processing, consider downloading the Wikidata JSON dump instead of SPARQL queries.

### BASE (OAI University Theses)
- **URL**: https://api.base-search.net/cgi-bin/BaseHttpSearchInterface.fcgi
- **Licence**: Mixed (depends on repository)
- **Daily quota**: Bulk dump available
- **Setup**: None. Public API.
- **Rate limits**: Be polite -- max 1-2 req/sec recommended.
- **What it provides**: Thesis title, institution, degree date, DOI
- **Adapter**: `src/authority/oai_university_adapter.py`

### HAL (French Open Archive)
- **URL**: https://api.archives-ouvertes.fr/search
- **Licence**: CC-BY
- **Daily quota**: 86,400 requests
- **Setup**: None. Public API.
- **What it provides**: Institution/lab affiliations from French research publications
- **Adapter**: `src/authority/hal_adapter.py`

### GND (German National Library)
- **URL**: https://lobid.org/gnd/search
- **Licence**: CC-BY
- **Daily quota**: Unlimited (lobid is a public service)
- **Setup**: None. Public API via lobid.org.
- **What it provides**: Preferred name form, birth/death years
- **Adapter**: `src/authority/gnd_adapter.py`

### zbMATH Open
- **URL**: https://api.zbmath.org
- **Licence**: CC-BY
- **Daily quota**: 200 requests
- **Setup**: None. Public API.
- **Rate limits**: Very low (200/day). Use cache aggressively.
- **What it provides**: zbMATH publication/author IDs
- **Adapter**: `src/authority/zbmath_open_adapter.py`
- **Note**: The low daily quota means zbMATH should only be used for targeted lookups, not bulk enrichment.

---

## Tier 2 -- Subscription Required

These sources require institutional or paid API access. Adapters exist as stubs that return `hit=False`.

### MathSciNet (AMS)
- **URL**: https://mathscinet.ams.org
- **Licence**: Subscription (American Mathematical Society)
- **Daily quota**: 20,000 requests
- **How to get access**:
  1. Your institution must have an AMS MathSciNet subscription
  2. Access is typically IP-based (campus network or VPN)
  3. For API access, contact AMS directly: mathscinet-support@ams.org
  4. There is no public API -- the adapter would need to parse HTML or use the MR Lookup service
  5. MR Lookup (free, limited): https://mathscinet.ams.org/mrlookup -- provides MR numbers for citations
- **What it would provide**: MathSciNet author ID (MR Author ID), publication list, MSC codes, co-author graph
- **Configuration**:
  ```bash
  export MATHSCINET_SESSION_COOKIE="..."  # from authenticated browser session
  # OR
  export MATHSCINET_PROXY="socks5://your-campus-proxy:1080"
  ```
- **Implementation status**: Stub only. Requires HTML parsing or MR Lookup integration.

### Scopus (Elsevier)
- **URL**: https://api.elsevier.com/content/search/author
- **Licence**: Elsevier Developer Agreement
- **Daily quota**: 20,000 requests
- **How to get access**:
  1. Go to https://dev.elsevier.com
  2. Create an account (free registration)
  3. Request an API key at https://dev.elsevier.com/apikey/manage
  4. Accept the API Terms of Use
  5. The free "non-commercial" tier provides 20K req/week for research purposes
  6. For higher limits, apply for the Elsevier Scopus APIs institutional programme
- **What it would provide**: Scopus Author ID, h-index, publication count, ORCID, affiliation history
- **Configuration**:
  ```bash
  export SCOPUS_API_KEY="your-api-key-here"
  # Optional: institutional token for higher limits
  export SCOPUS_INST_TOKEN="your-institutional-token"
  ```
- **API documentation**: https://dev.elsevier.com/documentation/AuthorSearchAPI.wadl
- **Implementation status**: Stub. Adapter skeleton exists; needs API key wiring.

### Dimensions (Digital Science)
- **URL**: https://app.dimensions.ai/api
- **Licence**: Digital Science Agreement
- **Daily quota**: 10,000 requests
- **How to get access**:
  1. Go to https://app.dimensions.ai
  2. Click "Get access" or visit https://www.dimensions.ai/scientometric-research/
  3. Free access is available for:
     - **Dimensions on Google BigQuery** (free for research via Google Cloud)
     - **Dimensions API** for non-commercial research (apply via form)
  4. Fill out the research application form explaining your use case
  5. Response typically takes 1-2 weeks
  6. For commercial use, contact sales@dimensions.ai
- **What it would provide**: Dimensions researcher ID, publication count, citation count, research categories, ORCID, affiliations
- **Configuration**:
  ```bash
  export DIMENSIONS_API_KEY="your-api-key-here"
  # OR use username/password auth:
  export DIMENSIONS_USERNAME="your-email"
  export DIMENSIONS_PASSWORD="your-password"
  ```
- **API documentation**: https://docs.dimensions.ai/dsl/
- **Implementation status**: Stub. Adapter skeleton exists; needs auth wiring.

---

## Tier 3 -- Restricted / Opt-In

### ProQuest Dissertations & Theses
- **URL**: https://www.proquest.com (institutional access)
- **Licence**: Commercial
- **Daily quota**: 50,000 requests
- **How to get access**:
  1. ProQuest requires an institutional subscription
  2. Contact your university library to check if they have ProQuest access
  3. For programmatic access, you need the ProQuest TDM Studio:
     - Apply at https://about.proquest.com/en/products-services/TDM-Studio/
     - Requires institutional agreement
  4. Alternative: Use ProQuest's Open Access subset (PQDT Open)
     - URL: https://pqdtopen.proquest.com
     - Free, but limited to voluntarily deposited dissertations
- **What it would provide**: Full dissertation metadata, advisor names, degree dates, institutions, abstracts
- **Configuration**:
  ```bash
  export PROQUEST_API_KEY="..."
  export PROQUEST_INST_CODE="..."  # institutional code
  ```
- **Implementation status**: Not implemented. Would need ProQuest TDM Studio API.

### Google Scholar
- **URL**: https://scholar.google.com
- **Licence**: Scraping (ToS violation risk)
- **Daily quota**: Undefined (aggressive rate limiting)
- **Access**: Public but heavily rate-limited and anti-bot protected
- **Opt-in mechanism**:
  ```bash
  export YES_I_ACCEPT_GS_TOS=yes
  python3 -m src.cli.gmnap process input.json --mode extreme --force-extreme
  ```
- **What it would provide**: Citation counts, co-author lists, publication venues
- **Implementation status**: Opt-in framework exists. Encrypted cache directory at `cache/gs/`. Actual scraping not implemented due to ToS concerns.

---

## Environment Variable Summary

```bash
# Tier 0 (optional, for polite pool)
export GMNAP_EMAIL="your-email@institution.edu"

# Tier 2 (required for paid sources)
export SCOPUS_API_KEY="..."
export DIMENSIONS_API_KEY="..."
export MATHSCINET_PROXY="..."

# Tier 3 (restricted)
export PROQUEST_API_KEY="..."
export YES_I_ACCEPT_GS_TOS=yes  # only if you accept Google Scholar ToS

# Pipeline control
export OFFLINE=0                 # enable live API calls (default: 1)
export PIPELINE_MODE=full        # quick (tier 0) / full (tier 0+1) / extreme (all)
```

---

## Recommended Approach

### Phase 1: Start with Tier 0 (immediate)
All tier 0 sources work out of the box. Set `OFFLINE=0` and run in Quick mode:
```bash
OFFLINE=0 python3 -m src.cli.gmnap process input.json --mode quick
```

### Phase 2: Add Tier 1 (immediate)
Run in Full mode to include rate-limited free sources:
```bash
OFFLINE=0 python3 -m src.cli.gmnap process input.json --mode full
```

### Phase 3: Add Scopus (1-2 days)
Easiest paid source to add. Register at dev.elsevier.com, get API key, set env var.

### Phase 4: Add Dimensions (1-2 weeks)
Apply for research API access. Wait for approval.

### Phase 5: MathSciNet (institutional)
Requires campus network or VPN. Most complex to automate due to HTML-based access.

### Phase 6: ProQuest (institutional)
Requires TDM Studio agreement. Best suited for batch thesis metadata extraction.
