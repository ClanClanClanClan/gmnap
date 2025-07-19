Global Mathematician‑Name Authority Project

Functional Specification — Version 6 (Standalone, Ultra‑Complete Edition)
Published 15 July 2025 – supersedes v5.

This document is the sole, normative contract for the design, construction and stewardship of a private, world‑scale, script‑aware knowledge‑base of mathematicians’ names. It contains every required term, data field, process, rule, test and milestone; no ancillary references are needed. Any implementation must conform to the present specification in its entirety.

⸻

0 Glossary

Term	Definition
Entry	One mathematician’s authority record (all names, identifiers, metadata).
Canonical Latin	Preferred Latin‑script form in “Family, Given” order (unless overridden by region rule).
Canonical Native	Authoritative form in the author’s own script; if the author publishes solely in Latin script this equals Canonical Latin.
Variant‑Observed	Object {str, source, accessed} exactly as seen in an external source.
Variant‑Synthesised	Object {str, type} where type ∈ {ascii-lossy, tone-number, diac-drop, order-swap, romanisation-alt, particle-drop, initial-collapse}.
FamilyNameType	Enumerated: surname (default), patronymic, mononym.
GlobalID	128‑bit truncated SHA‑256 (22 Base32 symbols) of {CanonicalNative, BirthYear?, DeathYear?}; if collision occurs append --1, --2, …
MSC	Object {code: 5‑digit string, source: authority}.
NameEvent	{type, year, from, to} with type ∈ {marriage, religious, passport, transition, legal_change, alias}.
LanguageOfPublication	ISO 639‑3 list (maximum 10 codes).
AffiliationTimeline	Optional list of {country, from, to} objects used for diaspora disambiguation.
Confidence	0 – 100 score calculated as a weighted linear combination; weights are stored in config/weights.yaml and must sum to 1.
Gender	Enumerated: male, female, nonbinary, unspecified. GenderProvided ∈ {true,false} records whether the value is self‑declared.
Pipeline Modes	Quick – tier‑0 APIs with local cache; Full – tier‑0 + tier‑1; Extreme – Full + tier‑2 scraping (requires --force‑extreme).
Catch‑All Group (R0)	Residual bucket for any ISO territory not explicitly mapped or any name with detector confidence < 50 %.
ShortFormClusters	Mapping {short_form → count} where count = number of distinct external occurrences of that short form.
GDPR_DATA flag	Boolean attached to every field that can directly identify a living person under EU GDPR.


⸻

1 Global coverage

### 1.1 Region Groups (41 + R0 + Z0)

Every ISO 3166 territory maps to exactly one region code. The authoritative mapping file data/region_index.csv is validated by continuous integration (CI).

Code	Region Group	ISO Territories	Primary Script(s)	Distinct Features
A1	Core Anglo‑Sphere	US GB CA AU NZ IE plus English‑Caribbean (AG AI BB BM BS DM GD GY JM KN LC MS TC TT VC VG VI) plus Pacific US territories (GU AS MP UM) plus FK	Latin ASCII	Middle initials; generational suffixes
A2	Western Europe	FR DE IT ES PT NL BE CH‑FR AT LU LI SM MC GI AD MT VA	Latin + diacritics	Iberian dual surnames; de/von/van particles
A3	Nordic–Baltic	DK NO SE FI IS FO AX EE LV LT	Latin + diacritics	Icelandic patronymic system
A4	Oceania Island States	FJ PG SB VU WS TO KI TV NR CK NU PF NC	Latin with macrons	Polynesian macron restoration
A5	Dutch/French Caribbean	CW SX BQ MQ GF GP RE YT PM	Latin	Apostrophes; Creole particles
B1	East‑Slavic	RU UA BY	Cyrillic	Patronymic endings; gender suffixes
B2	South‑Slavic & Central Europe	BG RS ME HR SI BA MK PL CZ SK HU RO AL XK	Latin & Cyrillic	Gaj alphabet; Hungarian name‑order flip
B3	Greek World	GR CY	Greek	ELOT 743 & ISO 843 romanisation
C1	Greater‑Turkic	TR AZ UZ TM KG KZ	Latin / Cyrillic / Arabic	Script reform schedules: UZ 2023–, TM 2019–, KZ 2023 → 2031
C2	Persian‑Tajik	IR AF TJ	Perso‑Arabic & Cyrillic	Ezāfe connectors; nisba elements; ISO 233‑3:2023 & DIN 31635
C3	Arabic Levant–Nile	IQ JO LB SY PS EG SD SS	Arabic	al‑ assimilation; root clustering
C4	Arabic Gulf	SA KW AE QA OM BH YE	Arabic	bin/bint, tribal nisba patterns
C5	Arabic Maghreb	MA DZ TN LY EH MR	Arabic	Ben… prefixes; French transliteration
C6	Hebrew & Diaspora	IL + diaspora	Hebrew	ISO 259 romanisation, optional niqqud
C7	Armenian	AM + diaspora	Armenian	Hübschmann–Meillet
C8	Georgian	GE	Georgian	ISO 9984 transliteration
C9	Caucasus‑Turkic	RU North‑Caucasus republics, AZ‑IR border	Mixed	Latin/Cyrillic/Arabic hybrids
D1	South Asia – Hindi Belt	IN‑HN NP BT	Devanagari	Initials; caste surnames
D2	South Asia – Dravidian	IN‑South LK‑TA	Tamil, Latin	Patronymic initials; mononyms
D3	South Asia – Bengali	BD IN‑WB TR AS	Bengali	Frequent script switching
D4	Pakistan & Urdu	PK	Urdu + Latin	bin/binte, Arabic loans
D5	Sinhala	LK‑SI	Sinhala	UN 2003 transliteration
E1	Sinophone Mainland	CN	Han‑Simplified	Pinyin vs Wade‑Giles
E2	Sinophone Traditional	TW HK MO	Han‑Traditional + Cantonese romanisation	
E3	Japan	JP	Kanji/Kana	Official order flip (2020)
E4	Korea	KR KP	Hangul & Hanja	Hyphen/space variation
E5	Vietnam	VN	Latin + diacritics	Numeric tone variants
E6	Mainland SEA	TH KH LA	Thai RTGS, Khmer UNGEGN, Lao MOICT 2019	
E7	Maritime SEA	ID MY SG BN PH TL	Latin	Malay bin/binti, Indonesian mononyms, Filipino maternal middle name
F1	SSA – Francophone	BJ BF CM CF CG CI DJ GA GN ML NE SN TG TD KM SC MG BI	Latin	Accented French particles
F2	SSA – Anglophone	GH NG KE UG TZ ZW ZM MW GM LR SL BW LS NA RW SZ MU SS	Latin	Hyphenated given names; middle initials
F3	Horn of Africa	ET ER	Geʽez	Patronymic chain (given‑father‑grandfather)
F4	Lusophone Africa	AO MZ CV GW ST	Latin	Portuguese particles
G1	Latin America & Iberian Caribbean	AR BO BR CL CO CR CU DO EC GT GY HN HT MX NI PA PE PY SV SR UY VE PR	Latin	Dual surnames; Portuguese diacritics
H1	Historical (≤ 1850)	Global pre‑1850	Mixed	Latinised names; epithets
R0	Residual Latin‑ASCII	Any unmapped code	Latin ASCII	Minimal matching rules
Z0	Quarantine	—	—	Detector confidence < 50 %

### 1.2 Diaspora overlay

config/diaspora.yaml supports non‑overlapping date ranges:

"TH":
  - {region: "E6", range: "-2015"}
  - {region: "A1", range: "2016-"}


⸻

2 YAML record schema (v1.5)

Version 1.5 is enforced by docs/schema.json.  New/changed fields are marked ★.

"<CanonicalLatin>":                       # top‑level key
  GlobalID:           "<sha256‑128bit>"   # Base32, 22 chars
  UpdatedAt:          "<ISO‑8601 UTC>"

  CanonicalLatin:     "<Family, Given>"
  CanonicalNative:    "<native script>"

  LanguageOfPublication: ["en", "es"]     # ≤ 10 codes
  AffiliationTimeline:                     # optional
    - {country: "US", from: 2016, to: null}

  Variants:
    Observed:
      - str: "García‑Marín, J. C."
        source: "MathSciNet"
        accessed: "2025-06-30"
    Synthesised:
      - str: "Garcia Marin Juan Carlos"
        type: "ascii-lossy"

  FamilyNameType: "surname"
  Gender: "male"
  GenderProvided: true                    # ★
  PreferredPronouns: ["he", "him"]        # ★

  BirthYear: 1978 | "1970s" | "-500" | "c1150" | "1150/1160"
  DeathYear: null

  CountryCodes:  ["ES"]
  DiasporaCodes: ["US:2011-"]             # optional

  PrimaryMSC:
    - {code: "60G15", source: "zbMATH"}

  NameEvents:
    - {type: "marriage", year: 2015,
       from: "Juan Carlos García",
       to:   "Juan Carlos García Marín"}

  Advisors: ["sha256-abc123--2"]          # optional

  ShortFormClusters:                      # ★
    "J. C. García": 4
    "García":       38

  AuthorityIDs:
    MathSciNet: "203000"
    ORCID:      "0000-0003-1111-2222"
    Scopus:     {id: "57189234567", license: "Elsevier"}
    RSL:        "0000123456"
    OpenAlex:   "A43637294"

  Confidence: 96
  RegionalExtras:
    primary_surname:   "García"
    secondary_surname: "Marín"
    ipa: "ɡaɾˈθi.a maˈɾin"
    confidence_components:
      id_score: 0.42
      script_certainty: 0.34
      msc_match: 0.15
      gender_certainty: 0.05

  Historic: false
  GDPR_DATA: false                        # ★
  SourceNote: "zbMATH scrape 2025‑06‑12"
  Comments: |
    Free‑form curator notes.


⸻

3 Region‑module interface

class RegionRuleError(Exception):
    """Entry fails region‑specific rule."""

class RegionSpec:
    code: str
    yaml_files: list[str]
    scripts: list[str]
    mixed_scripts: bool = False
    canonical_order: Literal[
        "Family, Given", "Given Family",
        "Patronymic", "Mononym"
    ]
    romanisation_standards: list[str]

    # mandatory hooks
    def clean(self, entry: dict)   -> None: ...
    def augment(self, entry: dict) -> None: ...
    def validate(self, entry: dict)-> None: ...
    def order_key(self, entry: dict)-> str: ...

    # optional bulk enrichment
    def batch_enrich(self, entries: list[dict]) -> None: ...

    # optional file‑level hooks
    def on_file_load(self, data: dict)  -> None: ...
    def before_write(self, data: dict)  -> None: ...
    def after_write(self, data: dict)   -> None: ...

order_key must be pure; CI calls it twice and compares results.

⸻

4 Processing pipeline

#	Stage	Key operations
0	Config	Load RegionSpecs; verify unique file ownership; check AuthorityIDs with proprietary licences include license field.
1	Ingest	Read YAML (ruamel); store raw text; Unicode flow = NFC → NFKD → custom fold → NFC.
2	Detect Region	Combine Unicode script ranges, ICU script detector, fastText lang‑ID, affiliation hints, DOI prefix, diaspora overlay. Tie‑breaker order: script > affiliation > DOI prefix > lang‑ID score.
3	Region hooks	Execute clean → augment → validate → order_key. Failures are routed to Z0 with human‑readable log.
4	Authority Enrich	Asynchronous aiohttp fetchers; quotas enforced; caches raw JSON/HTML (personal metadata scrubbed). Invalid payloads stored in cache/bad_json/ (purged in Stage 10).
5	Collision analytics	Build DuckDB tables initial_stats, surname_stats. If RAM > 2 GB required, automatically fall back to SQLite with partial index on (surname_prefix, birth_decade).
6	Tag short‑forms	Populate ShortFormClusters from analytics snapshot.
7	Global validate	Run JSON‑Schema; ensure unique GlobalIDs & external IDs; assert transliteration round‑trip rules.
8	Write & diff	Emit deterministic YAML (anchors & quotes preserved); produce HTML diff and SQL change‑log (changes.sqlite).
9	Report	Write Markdown summary plus metrics.json (runtime, new entries, warnings).
10	Idempotency check	Rerun stages 1 – 9 in a temp dir; compute SHA‑256 over (YAML set, collision DB, docs/, tests/, source_manifest.json); assert equality.

### 4.1 Runtime profiles

Mode	APIs queried	CPU workers	Warm‑cache runtime target (per 1 M)
Quick	tier‑0 only	4	≤ 30 min
Full	tier‑0 + tier‑1	unlimited	≤ 60 min
Extreme	Full + tier‑2	unlimited	no SLA

Streaming chunk size: 8 000 entries; peak memory limit ≤ 2 GB RSS (stress test).
Cache: Zstandard‐compressed, CACHE_MAX_SIZE_GB=20 or CACHE_MAX_DAYS=30.
Google Scholar HTML resides exclusively in cache/gs/.

⸻

5 Authority sources

Tier	Service	Key	Licence	Daily quota	Notes
0	OpenAlex	OpenAlex	CC0	864 000 (10 req/s)	Works, concepts, ORCIDs
	Crossref	Crossref	CC0	4.3 M	DOI metadata
	MathSciNet HTML	MathSciNet	Subscription	20 000	HTML parse
	zbMATH Open	zbMATH	CC‑BY	200	JSON
	ORCID	ORCID	CC0	500	REST
1	Scopus	Scopus	Elsevier	20 000	Starts Month 5
	Dimensions	Dimensions	Digital Science	10 000	Starts Month 5
	WoS ResearcherID	ResearcherID	Clarivate	5 000	
	DBLP	DBLP	CC‑BY	local	XML dump
	Math Genealogy Project	MGP	Public	local	SQL dump
	ISNI	ISNI	CC‑BY	28 800	REST
	GND	GND	CC‑BY	unlimited	SRU
	BNF IdRef	BNF	ODbL	unlimited	SPARQL
	Lattes	Lattes	CC‑BY	86 400	Brazilian CVs
	ADS	ADS	CC‑BY	86 400	astro‑math
	HAL	HAL	CC‑BY	86 400	French pre‑prints
	SciELO	SciELO	CC‑BY	86 400	LatAm/SSA
	RSL	RSL	CC‑BY	20 000	Russian e‑Library
	Magiran	Magiran	Scrape	10 000	optional
	Vidwan	Vidwan	REST	10 000	optional
	CNKI	CNKI	Subscription	10 000	e‑mail scrubbed
	CiNii	CiNii	Public	10 000	Japanese
	J‑STAGE	JStage	Public	10 000	Japanese
2	Google Scholar	GS	Scraping	undefined	Disabled unless --force‑extreme and YES_I_ACCEPT_GS_TOS=yes.

config/source_manifest.json records enabled, quota, licence for every source.

⸻

6 Cross‑region linguistic rule‑book

Thirty‑four deterministic rules govern normalisation and variant generation.
New or amended rules marked ★.
	1.	Iberian Dual Surname Split – stop‑words (de, del, de la, de las, de los, dos, das, y, e, delos) yield primary_surname, secondary_surname.
	2.	Arabic al‑ Article – normalise to root; sun‑letter assimilation; order_key omits article.
	3.	Arabic bin/bint – treated as patronymic, removed from order_key.
	4.	Vietnamese Tone Handling – generate full, ASCII and numeric‑tone (Nguyen3) variants.
	5.	Kazakh Script Switch – publications year ≥ 2027 use Latin transliteration; earlier use Cyrillic.
	6.	Turkish İ/i Ambiguity – produce dotted and dotless variants for ASCII sources.
	7.	Persian Ezāfe – connectors ‑e/‑ye ignored in order_key.
	8.	Icelandic Patronymic – FamilyNameType=patronymic; excluded from surname collision stats.
	9.	East‑Slavic Patronymic – strip middle token (Ivanovich) from Canonical Latin, infer gender.
	10.	Hungarian Name Order – generate both “Family Given” and Western order when detected.
	11.	CJK Round‑Trip – romanise and back‑convert Hanzi/Kana/Hangul; assert ≥ 97 % match.
	12.	Japanese Post‑2020 Order Rule – if ≥ 50 % of English papers (post‑2020) use Family Given, set canonical accordingly.
	13.	Korean Hyphen/Space – produce hyphen, space and concatenated variants; order_key collapsed.
	14.	Mononyms (ID/MM, ET/ER) – FamilyNameType=mononym; skip initials clustering.
	15.	Germanic Particles – von, van, de, etc., dropped in order_key (except d’).
	16.	Unicode Fold Exceptions – ligatures decomposed; ß/ẞ produce ss/SS variants; Greek tonos = oxia. ★
	17.	Iberian Honorific Strip – remove Dr., D., Dª, etc., when normalising.
	18.	Anglo Middle‑Initial Collapse – cluster “John C.” with “John”.
	19.	Greek Χατζη‑/Hadji‑ Variants – generate Haji‑, Hatzi‑ spellings.
	20.	Turkic ‑oğlu/‑ogly – move suffix to RegionalExtras.patronymic; omit in key.
	21.	‑zadeh Suffix – part of surname; hyphen preserved.
	22.	French d’ Particle – kept in order_key (d’Alembert).
	23.	SSA Hyphenated Given Names – initials “M.‑A.” and “M.” both computed.
	24.	Russian Transliteration – synthesise GOST 7.79‑2000 (A) and BGN‑PCGN 1947 spellings. ★
	25.	Greek Ancient Names – historic Latinised canonical; excluded from modern collisions.
	26.	Gender Heuristic Guard – heuristics applied only where validation accuracy ≥ 95 %.
	27.	Mainland SEA Romanisation – Thai RTGS spacing, Khmer UNGEGN, Lao MOICT 2019; generate ASCII variants.
	28.	Malay bin/binti – patronymic stripped for key; stored in extras.
	29.	Indonesian Mononyms – one‑token canonical; ShortFormClusters omitted.
	30.	Filipino Maternal Middle Name – middle token stored as secondary_surname.
	31.	Pacific Macron Restore – synthesise macronised Māori/Samoan/Tongan forms.
	32.	Ibn/Abu/Um Prefixes – prefix dropped for collision key when following token length ≥ 3.
	33.	Capital Sharp‑S Handling – canonical uppercase ẞ preserved in native forms, but variant generations include SS fallback. ★
	34.	Round‑trip Determinism – if any rule chain alters Canonical Latin, reciprocal transformation must restore the original string exactly. ★

Unit‑test fixtures (tests/fixtures/) require ≥ 95 % pass‑rate for each rule (100 % where noted).

⸻

7 Quality gates

Metric	Quick	Full	Extreme
Duplicate GlobalID	0	0	0
Duplicate external ID	0	0	0
Round‑trip deterministic scripts (CJK + Thai/Lao/Khmer)	≥ 97 %	≥ 97 %	≥ 97 %
Missing tier‑0 AuthorityID (living)	≤ 40 %	≤ 15 %	≤ 10 %
Non‑deterministic order keys (Δ between runs)	≤ 0.1 %	≤ 0.05 %	≤ 0.01 %
Peak RSS on 2 M synthetic entries	≤ 2 GB	≤ 2 GB	≤ 2 GB
Warm‑cache runtime / 1 M entries	≤ 30 min	≤ 60 min	—
Idempotent rerun diff size	0 bytes	0 bytes	0 bytes

Hard‑gate failures abort the pipeline.

⸻

8 Testing suite

Directory layout:
	•	unit/ – region hook logic, schema validation.
	•	property/ – hypothesis diacritic‑fold idempotence (incl. Arabic Hamza + Maddah, CJK full‑width punctuation).
	•	fixtures/ – 1 000 curated entries (≥ 1 per region).
	•	sea_roundtrip/ – Thai, Khmer, Lao round‑trip tests.
	•	concurrency/ – 8‑process stress test (thread‑safety, SIGINT graceful abort).
	•	memory_peak/ – validates RSS limit.
	•	msc_provenance/ – asserts every PrimaryMSC has source.
	•	fake_api/ – local stub server when OFFLINE=1.
	•	stress/ – 2 M synthetic names, weekly CI run.
	•	integration/ – live API smoke tests (skipped if OFFLINE=1).
	•	secret‑scan/ – blocks leaked secrets in logs or artefacts.

⸻

9 Security & legal
	•	Only identifiers are stored; proprietary metadata cached locally, never published.
	•	Sensitive fields carry GDPR_DATA=true; runtime flag --drop-personal removes them from output packages.
	•	CNKI, Magiran, RSL scrapers excise e‑mail/phone before caching.
	•	BirthYear is decade‑granular or null when < 5 authors share that year in the same country.
	•	LICENSE_RESTRICTIONS.md auto‑lists proprietary identifier keys present in the corpus.
	•	Google Scholar fetcher disabled unless --force‑extreme and environment variable YES_I_ACCEPT_GS_TOS=yes; HTML saved only under cache/gs/ for easy purge.
	•	ATTRIBUTION.txt auto‑generated each run, containing SPDX licence identifiers for all CC‑BY/SA sources.

⸻

10 Developer tooling
	•	Dev‑container: Ubuntu 22.04, Python 3.12, DuckDB 0.10, ruamel.yaml 0.18 (pinned), fastText lang‑ID model (installer script scripts/get_fasttext.sh), Zstandard CLI.
	•	Pre‑commit hooks: black, ruff, isort, codespell, yamllint.
	•	Makefile targets: quick, full, extreme, test, lint, update-sources.
	•	Spell‑checker: region dictionaries under tools/dictionaries/<region>.txt.
	•	CLI utilities:
	•	gmnap query "<surname, given>" → merged record.
	•	gmnap diff --author <GlobalID> → per‑author change log (from changes.sqlite).
	•	VS Code extension (Month 5): syntax highlighting, schema validation, formatter inserting narrow no‑break spaces (U+202F) before initials.

⸻

11 Project road‑map (solo academic timeline)

Month	Deliverables
1	Core pipeline; YAML schema v1.5; Region groups A1 – A5 complete; Quick nightly run with OpenAlex cache bootstrap.
2	Western Europe, Nordic/Baltic (A2 – A3), Central Europe (B2); Iberian surname rule; authority fetchers for OpenAlex, Crossref, zbMATH, ORCID online.
3	C‑groups & D‑groups fully implemented; SEA round‑trip logic passes ≥ 97 %; script‑switch logic for UZ, TM, KZ operational.
4	All E‑groups (E1 – E7); HAL, CiNii, J‑STAGE enrichers; Pacific macron rule green.
5	F‑groups; paid‑API integration (Scopus, Dimensions, WoS); RSL fetcher; stress & memory gates green; VS Code extension released.
6	Integration buffer, performance tuning, full legal audit, documentation polish; tag release v6.0.

A two‑week contingency is built into Month 6.

⸻

12 Change control

Any modification to this specification requires:
	1.	Incrementing the version number (v6 → v7).
	2.	Updating docs/schema.json, data/region_index.csv, affected fixtures and unit tests.
	3.	CI passing with new/updated tests.
	4.	Formal approval by the project maintainer.

⸻

End of Specification v6 — This document is fully self‑contained; implementation must follow it exactly.