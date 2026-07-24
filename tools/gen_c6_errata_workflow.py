#!/usr/bin/env python3
"""Emit the C6 errata re-adjudication workflow (R60.2 ruling 1).

The corpus-N+2 adjudication prompt carried a rule that turned out to be
wrong: it told adjudicators that Ashkenazi-associated surnames map to C6
"when the JEWISH identity of the name form is the dominant signal". That
instruction (a) contradicts the R58 pilot precedent, which adjudicated
German-form surnames like 'Rosenbaum' -> A2 by FORM, (b) contradicts the
codebase's own form-over-bearer rule (Abramovich -> B1, pinned in
tests/unit/test_signature_suffixes_turkic_balkan.py), and (c) asks an
adjudicator to infer ethnicity from a German-language surname, which is
both unreliable (Silberberg/Rosenberg have non-Jewish German bearers)
and not the axis this project classifies.

MAINTAINER RULING (2026-07-23): follow the FORM. German/Slavic-form
surnames take their form's leaf (A2 / B1 / B2). C6 is reserved for
genuinely Hebrew/Israeli name forms (Yashfe, Algom, Bar-Natan, Cohen,
Segal, Shalom, Katz).

Rather than bulk-rewriting 48+ labels by hand, this script emits a
small workflow that RE-ADJUDICATES exactly the C6-labeled names under
the corrected rule, with the same two-blind-lens + reconciler protocol.
Its output becomes the documented errata (the R58.7 pattern).

Run:  PYTHONPATH=. python3 tools/gen_c6_errata_workflow.py <out.js>
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
ADJ = REPO / "data" / "eval" / "heldout2" / "heldout2_adjudicated.json"

RULES = """
You are re-adjudicating the NAME-ORIGIN of mathematician author names
that a previous pass labeled C6 (Hebrew & Diaspora) under a rule that
has since been CORRECTED by the maintainer.

Name-origin means the etymology/orthography of the NAME ITSELF
(primarily the surname), NEVER the bearer's citizenship, ethnicity,
religion, affiliation, or workplace.

CORRECTED RULING — FOLLOW THE FORM:
- A surname whose FORM is German/Yiddish-German (Silberberg, Rosenbaum,
  Braunfeld, Weinstein, Kamnitzer, Kaplan) takes the GERMANIC leaf A2,
  regardless of the bearer population's ethnicity.
- A surname whose FORM is East-Slavic (Dvorkin, Etingof, Shehtman,
  Litchinitser, Bershtein, Soskin) takes B1. West/South-Slavic forms
  take B2.
- A surname whose FORM is Anglo takes A1.
- C6 is CORRECT ONLY for genuinely Hebrew/Israeli name forms: Hebrew
  lexical words and roots (Yashfe, Algom, Shalom, Sharon, Segal,
  Garti, Gelaki, Hanany, Zulti), Hebrew patronymic constructions
  (Bar-Natan, Ben-David), and the classical Jewish priestly/Levite
  surnames whose form is Hebrew rather than German (Cohen, Katz,
  Levy/Levi).
- Do NOT use the given name to infer the surname's origin. A Hebrew
  given name with a German-form surname is a Germanic-form surname
  (that is exactly the diaspora signal this project keeps on the geo
  axis, not the name axis).
- If the form is genuinely ambiguous between two families, output
  UNKNOWN rather than guessing.

Output one verdict per input name: leaf = one of the 34 leaf codes, or
"UNKNOWN". Confidence: "high" | "medium" | "low". Rationale <= 15 words
naming the FORM you judged.
"""


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    rows = json.load(open(ADJ))
    names = sorted({r["name"] for r in rows if r["leaf"] == "C6"})
    if not names:
        print("no C6 labels found — nothing to re-adjudicate")
        return 1

    taxonomy = REPO / "docs" / "region_taxonomy.txt"
    tax = taxonomy.read_text() if taxonomy.exists() else ""

    js = f"""export const meta = {{
  name: 'c6-errata-readjudication',
  description: 'Re-adjudicate C6-labeled names under the corrected form-wins ruling',
  phases: [
    {{ title: 'Adjudicate', detail: 'two blind lenses per chunk' }},
    {{ title: 'Reconcile', detail: 'per-chunk reconciler' }},
  ],
}}

const TAXONOMY = {json.dumps(tax)}
const NAMES = {json.dumps(names, ensure_ascii=False)}
const RULES = {json.dumps(RULES)} + '\\n\\nLeaf taxonomy:\\n' + TAXONOMY

const LABELS_SCHEMA = {{
  type: 'object', required: ['labels'],
  properties: {{ labels: {{ type: 'array', items: {{
    type: 'object', required: ['name', 'leaf', 'confidence', 'rationale'],
    properties: {{ name: {{ type: 'string' }}, leaf: {{ type: 'string' }},
      confidence: {{ enum: ['high', 'medium', 'low'] }}, rationale: {{ type: 'string' }} }} }} }} }},
}}
const FINAL_SCHEMA = {{
  type: 'object', required: ['labels'],
  properties: {{ labels: {{ type: 'array', items: {{
    type: 'object', required: ['name', 'leaf', 'agreement'],
    properties: {{ name: {{ type: 'string' }}, leaf: {{ type: 'string' }},
      agreement: {{ enum: ['both_agree', 'reconciled', 'unresolved'] }}, note: {{ type: 'string' }} }} }} }} }},
}}

const CHUNK = 25
const chunks = []
for (let i = 0; i < NAMES.length; i += CHUNK) chunks.push(NAMES.slice(i, i + CHUNK))
log(`re-adjudicating ${{NAMES.length}} C6 names in ${{chunks.length}} chunks`)

const LENSES = [
  'LENS A — surname MORPHOLOGY: which language does the surname stem and its affixes belong to?',
  'LENS B — orthographic SYSTEM: which language\\'s spelling conventions render this surname (German vs Slavic transliteration vs Hebrew romanization)?',
]

const out = await pipeline(
  chunks,
  (chunk, _o, idx) => parallel(LENSES.map((lens, li) => () =>
    agent(`${{RULES}}\\n\\nYour perspective: ${{lens}}\\nYou are BLIND to the other adjudicator and to the previous labels.\\n\\nRe-adjudicate these ${{chunk.length}} names (return every one):\\n${{chunk.map((n) => '- ' + n).join('\\n')}}`,
      {{ label: `errata-lens${{li === 0 ? 'A' : 'B'}}:chunk${{idx}}`, phase: 'Adjudicate', schema: LABELS_SCHEMA }}))),
  async (pair, chunk, idx) => {{
    const [a, b] = pair
    if (!a || !b) return null
    const merge = (why) => {{
      const bl = new Map(b.labels.map((l) => [l.name, l.leaf]))
      return {{ labels: a.labels.map((l) => bl.get(l.name) === l.leaf
        ? {{ name: l.name, leaf: l.leaf, agreement: 'both_agree', note: why }}
        : {{ name: l.name, leaf: 'UNKNOWN', agreement: 'unresolved', note: `${{why}}; A=${{l.leaf}} B=${{bl.get(l.name)}}` }}) }}
    }}
    const rec = await agent(`${{RULES}}\\n\\nYou are the RECONCILER. Two blind adjudicators re-labeled the same ${{chunk.length}} names under the corrected form-wins ruling. Keep agreed labels (agreement="both_agree"); decide disagreements yourself (agreement="reconciled"); output UNKNOWN + "unresolved" if neither is defensible. Return every name.\\n\\nLens A:\\n${{JSON.stringify(a.labels)}}\\n\\nLens B:\\n${{JSON.stringify(b.labels)}}`,
      {{ label: `errata-reconcile:chunk${{idx}}`, phase: 'Reconcile', schema: FINAL_SCHEMA }})
    return rec || merge('reconciler unavailable — mechanical lens merge')
  }},
)

const labels = out.filter(Boolean).flatMap((r) => r.labels)
return {{ labels, n: labels.length }}
"""
    Path(sys.argv[1]).write_text(js, encoding="utf-8")
    print(f"{len(names)} C6 names -> {sys.argv[1]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
