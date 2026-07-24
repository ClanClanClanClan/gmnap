"""Priority-rules scorer: lexicon, 3-tier suffix system, learned features.

Moved verbatim from ``manager_optimized.py`` (R45). The ``@functools.lru_cache``
on ``_wb`` is the round-28 22x-speedup unlock — do not remove it.
"""

import functools
import json
import logging
import os
import re
import unicodedata
from pathlib import Path

logger = logging.getLogger(__name__)

# Two token alphabets, deliberately different (R59.5):
#
# _WORD (RAW tokens): FULL Unicode letters ([^\W\d_]) — the old Latin-1
# class stopped at U+00FF, so č/ć/š/ž/ő/ū (Latin Extended-A) SPLIT the
# raw token ('čekanavičius' -> 'ekanavi'+'ius') and silently killed
# every raw-diacritic rule for those marks: the 'ović'/'ević' raw
# suffixes (documented as mysteriously dead), the -ovic dedupe guard,
# the Łacinka '-ovič' abstention, and the C9 'ičius' rule.
#
# _LATIN1_WORD (FOLDED tokens, _latin_tokens): the ORIGINAL Latin-1
# class, kept on purpose. _latin_tokens' isalnum() filter passes
# CJK/Greek/Cyrillic characters, so this class doubles as the de-facto
# SCRIPT GATE: a pure-CJK name must tokenize to [] ('no_tokens') so the
# manager falls through to script-based detection. Broadening it to
# Unicode letters routed 王小明 into the Latin scorer, whose 'no_signal'
# is a HARD abstain that shadowed the script tier (measured: every
# non-Latin native fell to R0 and stage-3 romanization died). Post-NFKD
# Latin text is inside Latin-1 (č -> c; ø/æ/ß don't decompose and are in
# the class), so folded tokens are byte-identical to the old behavior.
_WORD = re.compile(r"[^\W\d_]+(?:['-][^\W\d_]+)*")
_LATIN1_WORD = re.compile(r"[A-Za-zÀ-ÖØ-öø-ÿ]+(?:['-][A-Za-zÀ-ÖØ-öø-ÿ]+)*")


def _latin_tokens(name: str) -> list[str]:
    """Extract tokens from name, normalized and lowercased."""
    name_nfkd = unicodedata.normalize("NFKD", name).lower()
    # Turkish dotless ı (U+0131) has NO NFKD decomposition and sits outside
    # _WORD's [A-Za-zÀ-ÖØ-öø-ÿ] class, so 'yılmaz' used to tokenize as
    # 'y'+'lmaz' — silently killing every ı-bearing exact-surname entry and
    # suffix match. Fold it to plain 'i' like every other diacritic.
    name_nfkd = name_nfkd.replace("ı", "i")
    name_ascii = "".join(ch for ch in name_nfkd if ch.isalnum() or ch in "- '")
    return _LATIN1_WORD.findall(name_ascii)


@functools.lru_cache(maxsize=None)
def _wb(pattern: str) -> re.Pattern:
    """Whole word or hyphen-bounded pattern (e.g. 'Jae-in', 'Min-soo').

    Round-28 finding: this function was being called ~4 million times
    per 1k real-name batch, each recompiling the same 50-100 patterns.
    cProfile measured 357 s of cumulative time on a 379 s benchmark
    (94 % of total) just in regex re-compilation. The pattern set is
    bounded (priority lexicons are static at module load), so a
    process-wide unbounded LRU cache is correct and safe here. Memory
    cost: ~50-100 cached patterns * ~200 bytes = trivial. Speedup on
    real-name 1k benchmark: expected 30-50× (94 % time recovered).
    """
    return re.compile(
        rf"(?<![A-Za-zÀ-ÖØ-öø-ÿ]){re.escape(pattern)}(?![A-Za-zÀ-ÖØ-öø-ÿ])"
    )


# ---------- Priority lexicons (comprehensive coverage for all 37 regions) ----------
# Expanded from 13 regions to 37 regions based on Tier 1 validation results (2025-01-04)
# Total: 850+ surnames, 500+ given name patterns

_STRONG = {
    # ========== A GROUP: WESTERN/ANGLOPHONE ==========
    "A1": {  # Anglo-Sphere (USA, UK, Canada, Australia, New Zealand - core English)
        "surname_suffix": {
            "ington",  # Worthington, Wellington, Paddington
            "ingham",  # Buckingham, Cunningham, Birmingham
            "onald",  # McDonald, MacDonald, Ronald
        },
        "surname_prefix": {  # Handled specially below
            "o'",  # O'Brien, O'Sullivan, O'Malley
            "mc",  # McGregor, McCartney, McDonald
            "mac",  # MacDonald, MacLeod, MacArthur
            "fitz",  # FitzGerald, FitzPatrick
        },
        "surnames": {
            "smith",
            "johnson",
            "williams",
            "brown",
            "jones",
            "miller",
            "davis",
            "wilson",
            "anderson",
            "thomas",
            "taylor",
            "moore",
            "jackson",
            "white",
            "harris",
            "clark",
            "lewis",
            "robinson",
            "walker",
            "hall",
            "allen",
            "young",
            "king",
            "wright",
            "scott",
            "green",
            "baker",
            "adams",
            "nelson",
            "carter",
            "mitchell",
            "roberts",
            "turner",
            "phillips",
            "campbell",
            "parker",
            "evans",
            "edwards",
            "collins",
            "stewart",
            "morris",
            "murphy",
            "cook",
            "rogers",
            "morgan",
            "peterson",
            "cooper",
            "reed",
            "bailey",
            "bell",
            "howard",
            "ward",
            "cox",
            "richardson",
            "wood",
            "watson",
            "brooks",
            "kelly",
            "sanders",
            "price",
            "bennett",
            "barnes",
            "ross",
            "henderson",
            "coleman",
            "jenkins",
            "perry",
            "powell",
            "long",
            "patterson",
            "hughes",
            "washington",
            "butler",
            "simmons",
            "foster",
            "bryant",
            "alexander",
            "russell",
            "griffin",
            "hayes",
            "grant",
            "ferguson",
            "wallace",
            "griffiths",
        },
        "given_frag": {
            "john",
            "james",
            "robert",
            "michael",
            "william",
            "david",
            "richard",
            "joseph",
            "thomas",
            "charles",
            "christopher",
            "daniel",
            "matthew",
            "anthony",
            "donald",
            "mark",
            "paul",
            "steven",
            "andrew",
            "kenneth",
            "george",
            "joshua",
            "kevin",
            "brian",
            "edward",
            "ronald",
            "timothy",
            "mary",
            "patricia",
            "jennifer",
            "linda",
            "barbara",
            "elizabeth",
            "susan",
            "jessica",
            "sarah",
            "karen",
            "nancy",
            "betty",
            "margaret",
            "sandra",
            "ashley",
            "dorothy",
            "kimberly",
            "emily",
            "donna",
            "alex",
            "tony",
            "sam",
            "ben",
            "nick",
        },
    },
    "A2": {  # Western Europe (German, French, Italian, Dutch, Belgian, Swiss, Austrian, Portuguese)
        "surname_suffix": {
            "mann",
            "hofer",
            "stein",
            "berg",
            "feld",
            "elli",
            "otti",
            "ucci",
            "acci",
            # Portuguese-specific suffixes (not shared with Spanish)
            "eiro",
            "eira",
            "inho",
            "inha",
        },
        "surnames": {
            "müller",
            "schmidt",
            "schneider",
            "fischer",
            "weber",
            "meyer",
            "wagner",
            "becker",
            "schulz",
            "hoffmann",
            "schäfer",
            "koch",
            "richter",
            "klein",
            "wolf",
            "schröder",
            "neumann",
            "schwarz",
            "zimmermann",
            "braun",
            "dubois",
            "martin",
            "bernard",
            "thomas",
            "robert",
            "richard",
            "petit",
            "durand",
            "leroy",
            "moreau",
            "simon",
            "laurent",
            "lefebvre",
            "michel",
            "rossi",
            "russo",
            "ferrari",
            "esposito",
            "bianchi",
            "romano",
            "colombo",
            "ricci",
            "marino",
            "greco",
            "bruno",
            "gallo",
            "conti",
            "de jong",
            "jansen",
            "de vries",
            "van den berg",
            "bakker",
            "visser",
            "smit",
            "meijer",
            "de boer",
            "mulder",
            "de groot",
            "bos",
            "vos",
            "peters",
            "hendriks",
            "van dijk",
            "van leeuwen",
            "mazzucato",
            "ballantine",
            "opper",
            "cangini",
            "douçot",
            "taïbi",
            "monod",
            "abate",
            "bracci",
            "tovena",
            # R60.2 MAINTAINER RULING (2026-07-23): the 14-name
            # "Portuguese surnames (PT → A2)" block MOVED to G1 below.
            # Iberian-origin surnames — Spanish and Portuguese alike —
            # take G1; keeping Portuguese here while Spanish sat in G1
            # was the inconsistency corpus N+2 exposed. Moved, not
            # deleted: deleting would cost the whole class its coverage.
        },
        "particles": {
            "van",
            "von",
            "de",
            "del",
            "della",
            "di",
            "da",
            "den",
            "der",
            "la",
            "le",
            "du",
        },
        "given_frag": {
            "hans",
            "karl",
            # R59.5: 'kurt' was missing — 'Kurt Girstmair' (Austrian,
            # held-out corpus) scored 'kurt' against C1's STRONG surname
            # table (Kurt is also a common Turkish surname) and emitted
            # C1@0.875. As a known given name it is filtered from
            # no-comma surname candidates; comma'd 'Kurt, Mehmet' and
            # surname-last 'Mehmet Kurt' still fire C1 correctly.
            "kurt",
            "friedrich",
            "wolfgang",
            "helmut",
            "franz",
            "josef",
            "pierre",
            "jean",
            "françois",
            "michel",
            "philippe",
            "andré",
            "jacques",
            "luigi",
            "giuseppe",
            "franco",
            "antonio",
            "mario",
            "giovanni",
            "jan",
            "peter",
            "dirk",
            "lars",
            "erik",
            "hendrik",
            # Portuguese given names
            "joao",
            "goncalo",
            "nuno",
            "rui",
            "filipe",
            "diogo",
            "ines",
            "tiago",
            "catarina",
            "margarida",
            "duarte",
            "vasco",
            "bernardo",
        },
    },
    "A3": {  # Nordic-Baltic (Sweden, Norway, Denmark, Finland, Iceland, Baltic states)
        # R59.4: 'dottir' (ASCII, folded tokens) + 'dóttir' (raw tokens)
        # close the verified gap where ASCII-transliterated and non-s
        # weak-genitive Icelandic patronymics (Gudmundsdottir,
        # Finnbogadóttir, Helgadóttir) fell to R0 because only 'sdóttir'
        # existed and it never matches folded text.
        "surname_suffix": {"sen", "sson", "sdóttir", "sdotter", "dottir", "dóttir"},
        "surnames": {
            "andersson",
            "johansson",
            "karlsson",
            "nilsson",
            "eriksson",
            "larsson",
            "olsson",
            "persson",
            "svensson",
            "gustafsson",
            "pettersson",
            "jonsson",
            "hansen",
            "nielsen",
            "jensen",
            "pedersen",
            "andersen",
            "christensen",
            "larsen",
            "sørensen",
            "rasmussen",
            "jørgensen",
            "petersen",
            "madsen",
            "virtanen",
            "korhonen",
            "mäkinen",
            "nieminen",
            "mäkelä",
            "hämäläinen",
            "laine",
            "heikkinen",
            "koskinen",
            "järvinen",
            "lehtonen",
            "saari",
            "björnsson",
            "sigurðsson",
            "guðmundsson",
            "jónsson",
            "ólafsson",
            "kristjánsson",
            "kalniņš",
            "ozols",
            "bērziņš",
            "lok",
        },
        "given_frag": {
            "lars",
            "sven",
            "anders",
            "erik",
            "björn",
            "magnus",
            "olaf",
            "nils",
            "per",
            "gunnar",
            "ingmar",
            "kjell",
            "håkan",
            "sten",
            "ulf",
            "ingrid",
            "astrid",
            "karin",
            "liv",
            "margit",
            "solveig",
            "helga",
            "mikko",
            "jukka",
            "antti",
            "mika",
            "juha",
            "timo",
            "pekka",
        },
    },
    "A4": {  # Oceania (Australia, New Zealand, Pacific Islands)
        "surnames": {
            "tane",
            "rangi",
            "kapa",
            "aroha",
            "moana",
            "whakaari",
            "heke",
            "mahuta",
            "tupu",
            "henare",
            "parata",
            "tikao",
            "harawira",
            "waikato",
            "ngata",
            "tavita",
            "sione",
            "manu",
            "tui",
            "pule",
            "savea",
            "tagaloa",
            "faleolo",
            "fonoti",
            "taufa",
            "vunipola",
            "kanongata",
            "fifita",
            "taumoepeau",
            "katoa",
            "taufalele",
            "koloamatangi",
            "mundine",
            "goodes",
            "freeman",
            "perkins",
            "dodson",
        },
        "given_frag": {
            # Māori given names
            "aroha",
            "kiri",
            "wiremu",
            "hemi",
            "tane",
            "moana",
            "rangi",
            "whetu",
            "mere",
            "ngaire",
            "anahera",
            "kahu",
            "rewa",
            "wiki",
            "hine",
            "tama",
            "matiu",
            "mikaere",
            "hoani",
            "piripi",
            # Pacific Islander (Samoan, Tongan, Fijian)
            "tavita",
            "sione",
            "tui",
            "sina",
            "malia",
            "ana",
            "losa",
            "sefa",
            "ioane",
            "pita",
            "viliami",
            "semisi",
            "sione",
            "tevita",
            "lupe",
            "mele",
            "ateca",
            "vasiti",
            "salote",
            # European names common in Oceania (helps A4 vs A1 disambiguation)
            "emily",
            "amelia",
            "oliver",
            "james",
            "charlotte",
            "sophie",
            "ella",
            "grace",
            "william",
            "jack",
            "mia",
            "ava",
            "noah",
            "mason",
            "liam",
            "ruby",
            "chloe",
            "lucy",
            "thomas",
        },
    },
    "A5": {  # Caribbean (English/French/Dutch Caribbean)
        "surnames": {
            "joseph",
            "pierre",
            "jean",
            "baptiste",
            "francois",
            "charles",
            "louis",
            "paul",
            "etienne",
            "michel",
            "saint-vil",
            "saint-louis",
            "saint-juste",
            "williams",
            "brown",
            "davis",
            "robinson",
            "thompson",
            "lewis",
            "campbell",
            "reid",
            "graham",
            "morrison",
            "bailey",
            "stewart",
            "van der linden",
            "de groot",
            "jansen",
            "van den berg",
            "visser",
        },
        "given_frag": {
            "marcus",
            "andre",
            "jean-claude",
            "marie",
            "claudette",
            "yvette",
            "winston",
            "carlton",
            "dwayne",
            "shanique",
            "aaliyah",
            "kemar",
            "shaniqua",
            "delroy",
            "marlon",
        },
        "particles": {"saint", "de", "van"},
    },
    # ========== B GROUP: SLAVIC & GREEK ==========
    "B1": {  # East Slavic (Russian, Ukrainian, Belarusian)
        "surname_suffix": {
            "ov",
            "ova",
            "ev",
            "eva",
            "enko",
            "evich",
            "ovich",
        },
        "surnames": {
            "ivanov",
            "petrov",
            "sokolov",
            "smirnov",
            "kuznetsov",
            "popov",
            "lebedev",
            "kozlov",
            "novikov",
            "morozov",
            "volkov",
            "solovyov",
            "vasiliev",
            "zaytsev",
            "pavlov",
            "semenov",
            "golubev",
            "vinogradov",
            "bogdanov",
            "vorobiev",
            "fedorov",
            "mikhailov",
            "belyaev",
            "tarasov",
            "belova",
            "kovalev",
            "alekseev",
            "pitcyn",
            "moshchevitin",
            "solynin",
            "zalgaller",
        },
        "given_frag": {
            "alexander",
            "vladimir",
            "dmitry",
            "sergei",
            "nikolay",
            "victor",
            "andrei",
            "mikhail",
            "ivan",
            "alexei",
            "pavel",
            "yuri",
            "boris",
            "oleg",
            "anton",
            "igor",
            "maxim",
            "roman",
            "elena",
            "natalia",
            "olga",
            "irina",
            "svetlana",
            "tatiana",
            "marina",
            "yulia",
            "ekaterina",
        },
    },
    "B2": {  # South Slavic & Central (Polish, Czech, Slovak, Croatian, Serbian, Slovenian)
        "surname_suffix": {
            "wicz",
            "wski",
            "owski",
            "ewski",
            "ová",
            "ský",
            "ček",
            "ović",
            "ević",
            # ASCII South-Slavic patronymics (Petrovic, Markovic ... the
            # diacritic-stripped forms arXiv actually carries). Guarded in
            # the scoring loop: skipped when the raw name carries the
            # diacritic form (ović/ević/ovič/evič — the raw rules above
            # own those), and the French given name 'ludovic' (Ludovic
            # Rifford, Ludovic Goudenège) never counts.
            "ovic",
            "evic",
            # Romanian patronymic/toponymic suffixes (RO -> B2 in this
            # codebase's taxonomy): Popescu, Ionescu, Voiculescu;
            # Munteanu, Olteanu, Corduneanu. Guarded in the scoring
            # loop: 'francescu' (Corsican given name) never counts.
            "escu",
            "eanu",
        },
        "surnames": {
            "nowak",
            "kowalski",
            "wiśniewski",
            "wójcik",
            "kamiński",
            "lewandowski",
            "zieliński",
            "szymański",
            "woźniak",
            "dąbrowski",
            "kozłowski",
            "jankowski",
            "mazur",
            "krawczyk",
            "piotrowski",
            "novák",
            "svoboda",
            "novotný",
            "dvořák",
            "černý",
            "procházka",
            "nagy",
            "horváth",
            "kovács",
            "tóth",
            "varga",
            "horvat",
            "kovač",
            "babić",
            "marić",
            "jurić",
            "petrović",
            "nikolić",
            "jovanović",
            "popović",
            "đorđević",
            "stojanović",
            "ilić",
            "pavlović",
            "marković",
        },
        "given_frag": {
            "jan",
            "piotr",
            "andrzej",
            "tomasz",
            "jakub",
            "krzysztof",
            "václav",
            "petr",
            "jiří",
            "josef",
            "pavel",
            "martin",
            "ivan",
            "marko",
            "luka",
            "ante",
            "stjepan",
            "josip",
            "anna",
            "maria",
            "katarzyna",
            "zofia",
            "eva",
            "hana",
        },
    },
    "B3": {  # Greek & Cypriot
        # R59.4: 'idis'/'iadis' — corpus bearers 13/13 and 4/4 Greek
        # (Souganidis, Daniilidis, Garoufalidis, Antoniadis…). Excluded in
        # the scoring loop: davidis/aidis/naidis (Latin-German David-form,
        # Lithuanian). A token ending -iadis double-fires both (5.0, same
        # leaf — harmless, mirrors the sdóttir/dóttir pair).
        "surname_suffix": {"poulos", "akis", "opoulos", "ides", "idis", "iadis"},
        "surnames": {
            "papadopoulos",
            "papadakis",
            "papageorgiou",
            "dimitriou",
            "konstantinou",
            "georgiou",
            "nikolaou",
            "ioannou",
            "christodoulou",
            "vasiliou",
            "athanasiou",
            "michaelides",
            "antoniou",
            "savvidis",
            "makris",
            "pappas",
            "karagiannis",
            "alexandrou",
            "petrou",
            "charalambous",
            "andreou",
            "kyriakou",
            "philippou",
            "stavrou",
            "demetriou",
            "kottas",
            "athanasios",
        },
        "given_frag": {
            "georgios",
            "konstantinos",
            "dimitrios",
            "ioannis",
            "nikolaos",
            "andreas",
            "panagiotis",
            "christos",
            "michail",
            "alexandros",
            "vasileios",
            "athanasios",
            "spyros",
            "kostas",
            "maria",
            "eleni",
            "katerina",
            "sofia",
            "vasiliki",
            "georgia",
            "chrysoula",
            "despina",
            "anastasia",
            "ioanna",
        },
    },
    # ========== C GROUP: MIDDLE EAST & CAUCASUS ==========
    "C1": {  # Turkic (Turkish, Azerbaijani, Turkmen, Uzbek, Kazakh, Kyrgyz)
        # -maz/-mez: Turkish negative-aorist surname family (Yılmaz,
        # Korkmaz, Sönmez, Dönmez, Durmaz, Kaçmaz...). Guarded in the
        # scoring loop: consonant before the suffix (all verified
        # Hispanic/Romance bearers — Gómez, Gámez, Jaimez, Tomaz,
        # Grumaz — carry a vowel there), min length 6 (drops the
        # 2-letter-stem family Almaz/Elmaz/Ölmez where Ethiopian and
        # Albanian given-name collisions live), and the curated
        # exclusion 'gormaz' (Spanish toponymic, San Esteban de
        # Gormaz). -oglu: Turkish patronymic (Terzioğlu, Çavuşoğlu);
        # Greek renderings usually end -oglou, but bare ASCII -oglu on
        # Anatolian-Greek surnames is real ('Papasoglu, P.' -> B3,
        # adjudicated), so bare -oglu additionally requires Turkic
        # corroboration (orthographic marks or a C1 given-name hit) in
        # the scoring loop.
        "surname_suffix": {"maz", "mez", "oglu"},
        "surnames": {
            "yılmaz",
            "kaya",
            "demir",
            "şahin",
            "çelik",
            "yıldız",
            "aydın",
            "öztürk",
            "arslan",
            "doğan",
            "kılıç",
            "aslan",
            "çetin",
            "kara",
            "koç",
            "kurt",
            "özdemir",
            "şimşek",
            "erdoğan",
            "yavuz",
            "güneş",
            "karaca",
            "polat",
            "aliyev",
            "mammadov",
            "hasanov",
            "abdullayev",
            "ismaylov",
            "huseynov",
            "karimov",
            "rahimov",
            "akhmedov",
            "mamedov",
            "ibrahimov",
            "sultanov",
            "nazarov",
            "tursunov",
            "ergashev",
            "rakhmonov",
            "abbasov",
            "musayev",
            "guliyev",
            "rustamov",
            "babayev",
            "novruzov",
            "suleymanov",
            "akhundov",
            "gasimov",
        },
        "given_frag": {
            "mehmet",
            "ahmet",
            "mustafa",
            "ali",
            "hüseyin",
            "ibrahim",
            "ismail",
            "hasan",
            "yusuf",
            "osman",
            "ayşe",
            "fatma",
            "zeynep",
            "elif",
            "emine",
            "aziz",
            "rashid",
            "eldar",
            "javid",
            "samir",
            "farida",
            "leyla",
            "nurlan",
            "rashad",
            "vugar",
            "tural",
            "aysel",
            "gunay",
            "nigar",
            "timur",
            "ruslan",
            "alisher",
            "bekzod",
        },
    },
    "C2": {  # Persian-Tajik
        # R59.4: 'nezhad' — the other standard romanization of signature
        # 'nejad' (Hassannezhad, Ahmadinezhad); no non-Persian collision
        # class exists for the string.
        "surname_suffix": {"zadeh", "pour", "nejad", "nezhad", "khani"},
        "surnames": {
            "hosseini",
            "ahmadi",
            "mohammadi",
            "rezaei",
            "moradi",
            "karimi",
            "rahimi",
            "hashemi",
            "jafari",
            "kazemi",
            "rostami",
            "bagheri",
            "sadeghi",
            "khalighi",
            "mirzakhani",
        },
        "given_frag": {
            "mohammad",
            "ali",
            "hassan",
            "reza",
            "hossein",
            "mehdi",
            "ahmad",
            "fatima",
            "zahra",
            "maryam",
            "fatemeh",
            "nasrin",
            "shirin",
        },
    },
    "C3": {  # Arabic Levant & Nile (Syrian, Lebanese, Palestinian, Jordanian, Egyptian)
        "surname_prefix": {"al-", "el-"},
        "surnames": {
            "hussain",
            "tahir",
            "ahmad",
            "mohammed",
            "al-ahmad",
            "al-hassan",
            "al-khalil",
            "al-masri",
            "al-shami",
            "yousef",
            "ibrahim",
            "mansour",
            "khoury",
            "haddad",
            "nasser",
            "saleh",
            "farah",
            "said",
            "khalil",
            "abbas",
            "ali",
            "omar",
            "baker",
            "issa",
            "awad",
            "abdallah",
            "mubarak",
            "mahmoud",
            "hussein",
            "rashid",
            "hamdan",
        },
        "given_frag": {
            "mohammad",
            "ahmed",
            "hassan",
            "ali",
            "khalil",
            "omar",
            "youssef",
            "mahmoud",
            "ibrahim",
            "khaled",
            "said",
            "fadi",
            "rami",
            "tariq",
            "fatima",
            "aisha",
            "zaynab",
            "mariam",
            "layla",
            "sara",
            "nour",
            "dina",
            "hala",
            "reem",
            "maya",
        },
    },
    "C4": {  # Arabic Gulf (Saudi, Emirati, Kuwaiti, Bahraini, Qatari, Omani, Yemeni)
        "surname_prefix": {"al-"},
        "surnames": {
            "al-otaibi",
            "al-qahtani",
            "al-shammari",
            "al-harbi",
            "al-zahrani",
            "al-mutairi",
            "al-dosari",
            "al-ghamdi",
            "al-subaie",
            "al-rashid",
            "al-ali",
            "al-khalifa",
            "al-sabah",
            "al-thani",
            "al-nahyan",
            "al-maktoum",
            "al-said",
            "al-busaidi",
            "al-harthi",
            "al-balushi",
        },
        "given_frag": {
            "abdullah",
            "mohammed",
            "sultan",
            "khalid",
            "fahad",
            "saeed",
            "salem",
            "faisal",
            "turki",
            "abdul",
            "aziz",
            "rashid",
            "hamad",
            "nasser",
            "noura",
            "sarah",
            "hessa",
            "maha",
            "amal",
            "reem",
            "latifa",
        },
    },
    "C5": {  # Arabic Maghreb (Moroccan, Algerian, Tunisian, Libyan, Mauritanian)
        "surname_prefix": {"ben", "bou", "el-"},
        "surnames": {
            "belkacem",
            "benali",
            "bouazza",
            "el-fassi",
            "gharbi",
            "idrissi",
            "mansouri",
            "messaoudi",
            "rahmani",
            "slimani",
            "zaki",
            "boudiaf",
            "benmohamed",
            "bensaid",
            "boucherit",
            "cherif",
            "djamel",
            "hamza",
            "meziane",
            "nacer",
            "benabdallah",
            "benkhaled",
            "boutahar",
        },
        "given_frag": {
            "mohamed",
            "ahmed",
            "youssef",
            "karim",
            "amine",
            "rachid",
            "mustapha",
            "habib",
            "tarek",
            "sofiane",
            "mehdi",
            "fatima",
            "khadija",
            "aisha",
            "yasmine",
            "salma",
            "nadia",
            "samira",
            "amina",
            "leila",
            "soraya",
        },
    },
    "C6": {  # Hebrew & Jewish Diaspora
        "surnames": {
            "cohen",
            "levi",
            "mizrahi",
            "mizrachi",
            "katz",
            "shapiro",
            "goldman",
            "rosenberg",
            "friedman",
            "klein",
            "schwartz",
            "weiss",
            "stein",
            "berg",
            "roth",
            "green",
            "bernstein",
            "kaplan",
            "levine",
            "newman",
            "rosenfeld",
            "rubin",
            "silver",
            "wasserman",
            "blum",
            "abramson",
            "davidovich",
            "israeli",
            "sharon",
            "peres",
            "netanyahu",
            "ben-david",
            "ben-zion",
            "shalom",
            "yehuda",
        },
        "given_frag": {
            "david",
            "michael",
            "daniel",
            "benjamin",
            "jacob",
            "isaac",
            "abraham",
            "moses",
            "aaron",
            "samuel",
            "joseph",
            "nathan",
            "eli",
            "ari",
            "uri",
            "sarah",
            "rachel",
            "rebecca",
            "leah",
            "esther",
            "ruth",
            "hannah",
            "miriam",
            "avraham",
            "yitzhak",
            "moshe",
            "yosef",
            "yehuda",
        },
    },
    "C7": {  # Armenian
        "surname_suffix": {"yan"},
        "surnames": {
            "vardanyan",
            "petrosyan",
            "grigoryan",
            "sargsyan",
            "hakobyan",
            "martirosyan",
            "davtyan",
            "avetisyan",
            "hovhannisyan",
            "khachatryan",
            "karapetyan",
            "hambardzumyan",
        },
        "given_frag": {
            "armen",
            "tigran",
            "hayk",
            "aram",
            "gevorg",
            "narek",
            "ani",
            "lilit",
            "anahit",
            "lusine",
            "gohar",
            "mariam",
        },
    },
    "C8": {  # Georgian
        "surname_suffix": {"dze", "shvili", "adze"},
        "surnames": {
            "beridze",
            "gelashvili",
            "kapanadze",
            "kiknadze",
            "lortkipanidze",
            "mgeladze",
            "ninidze",
            "shengelia",
            "tskhadaia",
            "zedginidze",
            "gogoladze",
            "kipiani",
            "mchedlidze",
            "robakidze",
            "saakashvili",
            "abashidze",
            "bagrationi",
            "chkuaseli",
            "dolidze",
            "gachechiladze",
        },
        "given_frag": {
            "giorgi",
            "davit",
            "levan",
            "nikoloz",
            "irakli",
            "gigi",
            "lasha",
            "ana",
            "mariam",
            "tamar",
            "nino",
            "salome",
            "ketevan",
            "natia",
        },
    },
    "C9": {  # Baltic (Lithuanian, Latvian)
        "surname_suffix": {
            "auskas",
            "aitis",
            "evicius",
            "unas",
            "enas",
            "onis",
            "utis",
        },
        "surnames": {
            "kazlauskas",
            "jankauskas",
            "petrauskas",
            "stankevicius",
            "berzins",
            "ozolins",
            "liepa",
            "paulauskas",
            "butkus",
            "ramanauskas",
            "grinius",
            "landsbergis",
            "brazauskas",
            "adamkus",
        },
        "given_frag": {
            "vytautas",
            "mindaugas",
            "giedrius",
            "jonas",
            "antanas",
            "rasa",
            "daiva",
            "janis",
            "aldis",
            "edgaras",
        },
    },
    # ========== D GROUP: SOUTH ASIA ==========
    "D1": {  # South Asia Hindi Belt
        "surnames": {
            "singh",
            "kumar",
            "sharma",
            "gupta",
            "verma",
            "yadav",
            "tiwari",
            "pandey",
            "bansal",
            "bal",
            "mohan",
            "nair",
            "paudel",
            "mishra",
            "jain",
            "agarwal",
            "agrawal",
            "joshi",
            "patel",
            "shah",
            "sreenadh",
        },
        "given_frag": {
            "rajesh",
            "vijay",
            "prashant",
            "sanjay",
            "pratap",
            "indranil",
            "sagar",
            "manil",
            "bishnu",
            "amit",
            "suresh",
            "anil",
            "priya",
            "neha",
            "pooja",
            "anjali",
            "deepak",
            "rahul",
            "rohit",
        },
    },
    "D2": {  # South Asia Dravidian (Tamil, Telugu, Kannada, Malayalam)
        "surnames": {
            "krishnan",
            "subramanian",
            "venkatesh",
            "raman",
            "narayanan",
            "ramanathan",
            "sundaram",
            "iyer",
            "iyengar",
            "aiyar",
            "sastry",
            "reddy",
            "naidu",
            "rao",
            "murthy",
            "murty",
            "prasad",
            "kumar",
            "nair",
            "pillai",
            "menon",
            "warrier",
            "namboothiri",
            "panicker",
            "nandakumar",
            "venkataraman",
            "srinivasan",
            "chandrasekaran",
            "subramaniam",
            "balakrishnan",
        },
        "given_frag": {
            "venkatesh",
            "subramaniam",
            "ramesh",
            "shankar",
            "rajesh",
            "ganesh",
            "lakshmi",
            "priya",
            "divya",
            "meera",
            "radha",
            "arjun",
            "krishna",
            "balaji",
            "srinivas",
            "anand",
            "vijay",
            "nanda",
        },
    },
    "D3": {  # South Asia Bengali
        "surnames": {
            "biswas",
            "chatterjee",
            "banerjee",
            "mukherjee",
            "chakraborty",
            "ghosh",
            "sengupta",
            "roy",
            "das",
            "bose",
            "dutta",
            "sarkar",
            # R59.2: "dan" and "paul" removed — both are extremely common
            # Western GIVEN names; at STRONG(5.0) they hijacked given-name
            # tokens (the given name 'Dan' in a Romanian full name ->
            # D3@0.875). Bengali Paul/Dan bearers still resolve via other
            # evidence.
            "khatun",
        },
        "given_frag": {
            "indranil",
            "sourav",
            "arijit",
            "aniruddha",
            "priyanka",
            "swati",
            "rina",
            "soma",
            "tanmoy",
            "abhijit",
            "arindam",
            "prasenjit",
            "ananyo",
            "niharika",
            "khadija",
        },
    },
    "D4": {  # Pakistan Urdu
        "surname_suffix": {"ullah"},
        "surnames": {
            "khan",
            "ahmed",
            "ali",
            "hassan",
            "hussain",
            "shah",
            "malik",
            "rahman",
            "siddiqui",
            "qureshi",
            "chaudhry",
            "akhtar",
            "rizvi",
            "butt",
            "sheikh",
            "ansari",
            "aziz",
            "haider",
            "javed",
            "raza",
            "iqbal",
            "nawaz",
            "nazir",
            "bokhari",
        },
        "given_frag": {
            "muhammad",
            "ahmed",
            "ali",
            "hassan",
            "usman",
            "bilal",
            "hamza",
            "omar",
            "imran",
            "fahad",
            "kamran",
            "asif",
            "tariq",
            "ayesha",
            "fatima",
            "sana",
            "zainab",
            "maryam",
            "hina",
            "nida",
            "ashfaque",
            "mukhtar",
        },
    },
    "D5": {  # Sinhala (Sri Lankan)
        "surnames": {
            "fernando",
            "perera",
            "silva",
            "de silva",
            "jayawardena",
            "wickramasinghe",
            "gunawardena",
            "rajapaksa",
            "bandara",
            "kumara",
            "dissanayake",
            "senanayake",
            "jayasuriya",
            "wijesinghe",
            "ratnayake",
            "gunasekara",
            "peiris",
            "mendis",
            "amarasekara",
            "karunaratne",
            "pathirana",
            "weerasinghe",
        },
        "given_frag": {
            "pradeep",
            "chandana",
            "nuwan",
            "dinesh",
            "chaminda",
            "mahela",
            "kumari",
            "sanduni",
            "dilani",
            "nirosha",
            "priyanka",
            "chathurika",
        },
    },
    # ========== E GROUP: EAST/SOUTHEAST ASIA ==========
    "E1": {  # Sinophone Mainland (Pinyin)
        "surnames": {
            "wang",
            "zhang",
            "liu",
            "chen",
            "yang",
            "huang",
            "lu",
            "shen",
            "li",
            "zhao",
            "qian",
            "fu",
            "mok",
            "chung",
            # R58.8: "pang" removed — Korean 방 shares the romanization
            # ("Pang, Min-su" fired STRONG_SURNAME:pang:5.00 -> E1).
            "hang",
            "lie",
            "sun",
            "zhou",
            "gao",
            "wu",
            "xu",
            "zhu",
            "deng",
            "mao",
            "cai",
        },
        "given_frag": {
            "xiao",
            "yi",
            "hao",
            "wei",
            "ying",
            "yong",
            "yifan",
            "zhe",
            "pang",
            "fang",
            "ming",
            "li",
            "jing",
            "lei",
            "tao",
            "jun",
            "yan",
            "hua",
            "qiang",
            "xia",
            "hong",
            "peng",
            "bin",
        },
        "hyphen_given": False,
    },
    "E2": {  # Traditional Chinese (Taiwan Wade-Giles, Hong Kong Cantonese)
        "surnames": {
            "lin",
            "hsueh",
            "yung",
            "chen",
            "huang",
            "wu",
            "cheng",
            "tsai",
            "yang",
            "hsu",
            "liao",
            "chan",
            "wong",
            "cheung",
            "chow",
            "ng",
            "lau",
            "leung",
        },
        "given_frag": {
            "chih-wei",
            "hsin-yi",
            "yu-chen",
            "shih-hao",
            "ching-ying",
            "ka-ming",
            "siu-fung",
            "wai-keung",
            "yuk-lin",
        },
        "hyphen_given": True,
    },
    "E3": {  # Japanese
        "surname_suffix": {"moto", "kawa", "zaki", "hara", "mura", "yama"},
        "given_suffix": {
            "taro",
            "jiro",
            "ko",
            "hiko",
            "moto",
            "nori",
            "ki",
            "mi",
            "ya",
        },
        "surnames": {
            "sato",
            "suzuki",
            "takahashi",
            "tanaka",
            "watanabe",
            "ito",
            "yamamoto",
            "nakamura",
            "kobayashi",
            "kato",
            "yoshida",
            "yamada",
            "sasaki",
            "yamaguchi",
            "matsumoto",
            "inoue",
            "kimura",
            "hayashi",
            "shimizu",
            "saito",
            "endo",
            "fujita",
            "okada",
            "goto",
            "hasegawa",
            "murakami",
            "kondo",
            "ishikawa",
            "maeda",
            "fujii",
            "ogawa",
            "takeuchi",
            "kaneko",
            "fukuda",
            "oka",
            "tanimoto",
        },
        "given_frag": {
            "yuki",
            "haruto",
            "sota",
            "yuito",
            "hinata",
            "takuya",
            "kenji",
            "hiroshi",
            "toshiro",
            "kazuo",
            "akira",
            "noboru",
            "makoto",
            "sakura",
            "aoi",
            "hina",
            "yui",
            "rin",
            "mei",
            "yuko",
            "ayumi",
        },
    },
    "E4": {  # Korea
        "surnames": {
            "kim",
            "lee",
            "park",
            "choi",
            "jung",
            "jeon",
            "kang",
            "cho",
            "yoon",
            "jang",
            # R58.8: "lim" REMOVED from the scorer's STRONG set — it is
            # equally the Hokkien 林 romanization ('Lim Chin Siong' fired
            # STRONG_SURNAME:lim:5.00 -> E4). The manager's surname tier
            # upstream keeps Korean Lims via its given-name disambiguation
            # ('Lim, Jae-woo' -> E4 there); the scorer has no such machinery.
            "han",
            "oh",
            "seo",
            "shin",
            "kwon",
            "ryu",
            "ahn",
            "moon",
            "song",
            "hwang",
            "bae",
            "yoo",
            "hong",
            "noh",
            "roh",
            "pak",
            "rhee",
            "choe",
            "ha",
            "baek",
        },
        "given_frag": {
            "seung",
            "hyun",
            "min",
            "soo",
            "hee",
            "young",
            "jae",
            "min-jun",
            "seo-jun",
            "do-yoon",
            "si-woo",
            "ji-ho",
            "seo-yeon",
            "min-seo",
            "ha-yoon",
            "ji-woo",
            "soo-a",
            "hyun-woo",
        },
        "hyphen_given": True,
    },
    "E5": {  # Vietnam
        "surnames": {
            "nguyen",
            "tran",
            "le",
            "pham",
            "hoang",
            "vo",
            "duc",
            "hieu",
            "phan",
            "vu",
            "dang",
            "bui",
            "do",
            "ngo",
            "duong",
            "ly",
        },
        "particles": {"van", "thi"},
        "given_frag": {
            "minh",
            "tuan",
            "huy",
            "duc",
            "hung",
            "linh",
            "anh",
            "huong",
            "mai",
            "lan",
            "phuong",
            "thu",
            "van",
        },
    },
    "E6": {  # Mainland SEA (Thai, Lao, Khmer, Myanmar)
        "surnames": {
            "rattanakosin",
            "srisawat",
            "chaiyaporn",
            "prayoonwong",
            "sukhumvit",
            "charoenrat",
            "sirivat",
            "vongkham",
            "thepsuthin",
            "kasemsan",
            "phongsavanh",
            "souphanouvong",
            "sisavath",
            "chanthavong",
            "soukkhavong",
            "vongxay",
            "phomsavanh",
            "sok",
            "chan",
            "chea",
            "prak",
            "chhay",
            "seng",
            "sam",
            "kong",
            "kyaw",
            "aung",
            "win",
            "htun",
            "myint",
            "oo",
            "hlaing",
            "thein",
        },
        "given_frag": {
            "somchai",
            "somporn",
            "siriporn",
            "nittaya",
            "chaiyaporn",
            "bouasone",
            "khamla",
            "phonethip",
            "vanida",
            "sovann",
            "sophea",
            "srey",
            "chanthy",
            "aung",
            "kyaw",
            "mya",
            "soe",
            "thida",
            "san",
        },
    },
    "E7": {  # Maritime SEA (Indonesian, Malay, Filipino)
        "surnames": {
            "sukarno",
            "widodo",
            "suharto",
            "habibie",
            "susilo",
            "jokowi",
            "gunawan",
            "pranowo",
            "setiawan",
            "wijaya",
            "kusuma",
            "firmansyah",
            "santoso",
            "abdullah",
            "rahman",
            "ahmad",
            "ismail",
            "hassan",
            "ali",
            "mohamed",
            "yusof",
            "ibrahim",
            "osman",
            "hamid",
            "yaakob",
            "sulaiman",
            "santos",
            "reyes",
            "cruz",
            "bautista",
            "garcia",
            "ramos",
            "mendoza",
            "flores",
            "gonzales",
            "castro",
            "rivera",
            "gomez",
            "torres",
            "morales",
        },
        "given_frag": {
            "budi",
            "agus",
            "siti",
            "dewi",
            "andi",
            "irfan",
            "dian",
            "ahmad",
            "fatimah",
            "nurul",
            "aziz",
            "ali",
            "jose",
            "maria",
            "juan",
            "ana",
            "miguel",
            "rosa",
            "carlos",
        },
    },
    # ========== F GROUP: SUB-SAHARAN AFRICA ==========
    "F1": {  # SSA Francophone + North African Maghreb (Senegal, Mali, Algeria, Morocco, Tunisia)
        "surname_prefix": {"ben", "bou"},
        "surnames": {
            # Maghreb surnames
            "benali",
            "bousaid",
            "bouzid",
            "belkacem",
            "benamara",
            "khelifi",
            "messaoudi",
            "boudiaf",
            "slimani",
            "mebarki",
            "hamidi",
            "djebbar",
            "zeroual",
            "bouteflika",
            # West African surnames
            "diop",
            "ndiaye",
            "fall",
            "sow",
            "ba",
            "sy",
            "diallo",
            "toure",
            "keita",
            "traore",
            "ouedraogo",
            "kabore",
            "kone",
            "coulibaly",
            "sangare",
            "cisse",
            "dembele",
            "diabate",
            "kante",
            "camara",
            "bamba",
            "ouattara",
        },
        "given_frag": {
            "mamadou",
            "ousmane",
            "abdoulaye",
            "ibrahima",
            "moussa",
            "seydou",
            "fatou",
            "aminata",
            "mariam",
            "aissatou",
            "kadiatou",
            "fatoumata",
            "adama",
            "bakary",
            "cheikh",
            "lamine",
            # Maghreb given names
            "rachid",
            "driss",
            "nabil",
            "youssef",
            "khadija",
            "houria",
            "zineb",
            "said",
            "tahar",
            "larbi",
        },
    },
    "F2": {  # SSA Anglophone (Nigeria, Ghana, Kenya, Uganda, Tanzania, Zimbabwe)
        "surname_prefix": {"ade", "ola", "ogun", "ojo"},
        "surnames": {
            "adesanya",
            "ogundimu",
            "adeyemi",
            "olaniyan",
            "ogundipe",
            "afolabi",
            "okonkwo",
            "nwankwo",
            "eze",
            "okoro",
            "nwosu",
            "okafor",
            "uzoma",
            "chukwu",
            "adebayo",
            "oluwaseun",
            "adekunle",
            "ayodele",
            "babatunde",
            "oluwole",
            "mensah",
            "owusu",
            "boateng",
            "appiah",
            "osei",
            "asante",
            "adjei",
            "agyei",
            "kipchoge",
            "kamau",
            "ochieng",
            "njoroge",
            "wanjiru",
            "mwangi",
            "kariuki",
            "mugabe",
            "moyo",
            "ncube",
            "dube",
            "sibanda",
            "ndlovu",
            "nyathi",
            "tumwesigye",
            "ddamulira",
            "behakanira",
        },
        "given_frag": {
            "chukwuemeka",
            "oluwaseun",
            "chiamaka",
            "oluwatobi",
            "adebayo",
            "kofi",
            "kwame",
            "akosua",
            "abena",
            "yaa",
            "kamau",
            "wanjiru",
            "njeri",
            "muthoni",
            "thabo",
            "sipho",
            "zanele",
            "nomsa",
        },
    },
    "F3": {  # Horn of Africa (Ethiopian, Eritrean, Somali, Djiboutian)
        "surnames": {
            "tesfaye",
            "bekele",
            "negash",
            "haile",
            "wolde",
            "gebre",
            "kebede",
            "tadesse",
            "getachew",
            "asefa",
            "tsegaye",
            "mulugeta",
            # R59.5: 'solomon' REMOVED — cross-group ambiguous form
            # (Ethiopian patronymic F3, Hebrew C6, Anglo A1 bearers all
            # common; held-out counterexample 'Noah Solomon' adjudicated
            # C6 emitted F3@0.875). No single leaf admissible; abstain.
            "yohannes",
            "mohamed",
            "hassan",
            "ahmed",
            "ali",
            "abdi",
            "omar",
            "abdullahi",
            "osman",
            "farah",
            "aden",
            "hussein",
            "mohamud",
            "jama",
            "ismail",
        },
        "given_frag": {
            "abebe",
            "haile",
            "yohannes",
            "mulugeta",
            "alemayehu",
            "dawit",
            "fatima",
            "aisha",
            "amina",
            "hawa",
            "mohamed",
            "hassan",
            "abdi",
            "ahmed",
            "ali",
            "omar",
        },
    },
    "F4": {  # Lusophone Africa (Angola, Mozambique, Cape Verde, Guinea-Bissau)
        "surnames": {
            "dos santos",
            "fernandes",
            "gomes",
            "silva",
            "pereira",
            "neto",
            "tavares",
            "machado",
            "lopes",
            "rodrigues",
            # R58.8: manuel/antonio/jose/francisco/eduardo/carlos REMOVED —
            # they are Iberian GIVEN names, not Lusophone-African surnames,
            # and as 5.0-weight STRONG surnames they emitted F4 for any
            # 'X, Carlos Eduardo' ('Bortolotti, Carlos Eduardo' -> F4@0.88;
            # true A2-Italian diaspora). They remain in given_frag below,
            # which is their correct role.
            "marques",
            "sousa",
            "costa",
            "alves",
        },
        "given_frag": {
            "joão",
            "antonio",
            "carlos",
            "josé",
            "manuel",
            "francisco",
            "pedro",
            "maria",
            "ana",
            "isabel",
            "beatriz",
            "luisa",
            "paula",
        },
    },
    # ========== G GROUP: LATIN AMERICA ==========
    "G1": {  # Latin America (Spanish & Portuguese Americas)
        "surname_suffix": {"ez", "az", "iz", "oz"},
        # R60.1: STRONG surname sets match FOLDED (ASCII) tokens, so the
        # accented entries (gómez, gonzález, pérez, sánchez, ramírez,
        # díaz, gutiérrez) were DEAD — those names only reached G1 via
        # the weaker -ez suffix (2.5), and 'Gomez' lost outright to E7's
        # ASCII entry (5.0): 'Gomez, Maria' emitted E7@0.89. ASCII forms
        # restore the symmetric G1-vs-E7 competition the other shared
        # Filipino-Hispanic surnames already have (given evidence
        # decides, like Mendoza).
        "surnames": {
            "garcia",
            "rodriguez",
            "martinez",
            "lopez",
            "roman",
            "hernandez",
            "gonzalez",
            "perez",
            "sanchez",
            "ramirez",
            "torres",
            "flores",
            "rivera",
            "gomez",
            "diaz",
            "cruz",
            "morales",
            "reyes",
            "gutierrez",
            "ortiz",
            "mendoza",
            # R60.2 ruling: Lusophone surnames moved here from A2 (see
            # the note at A2's surname set). Spanish and Portuguese
            # Iberian-origin surnames both resolve G1.
            "pinto",
            "soares",
            "correia",
            "teixeira",
            "gomes",
            "lopes",
            "pereira",
            "almeida",
            "carvalho",
            "ferreira",
            "coelho",
            "nogueira",
            "figueiredo",
            "azevedo",
        },
        "given_frag": {
            "josé",
            "juan",
            "carlos",
            "miguel",
            "luis",
            "jorge",
            "pedro",
            "diego",
            "maria",
            "ana",
            "laura",
            "carmen",
            "sofia",
            "gabriela",
            "isabella",
        },
    },
    # ========== SPECIAL REGIONS ==========
    "H1": {  # Historical (Latin, Sanskrit, Classical - mononyms, patronymic patterns)
        "surnames": {
            "euclid",
            "archimedes",
            "apollonius",
            "diophantus",
            "ptolemy",
            "pythagoras",
            "eratosthenes",
            "hypatia",
            "theon",
            "pappus",
            "brahmagupta",
            "aryabhata",
            "bhaskara",
            "varahamihira",
            "mahavira",
            "al-khwarizmi",
            "al-kindi",
            "al-biruni",
            "al-haytham",
            "khayyam",
        },
    },
}

# Near-diagnostic suffixes -- kept in handcrafted with full weight.
# Expert recommendation: only signature markers stay curated.
SIGNATURE_SUFFIXES = {
    "opoulos",
    "poulos",
    "akis",
    "ides",  # B3 Greek
    "shvili",
    "dze",
    "adze",  # C8 Georgian
    "yan",  # C7 Armenian
    "ov",
    "ova",
    "ev",
    "eva",
    "enko",
    "evich",
    "ovich",  # B1 East Slavic
    "sson",
    "sen",  # A3 Nordic
    "zadeh",
    "pour",
    "nejad",  # C2 Persian
    "mann",
    "stein",  # A2 Germanic (very distinctive)
    "maz",
    "mez",
    "oglu",  # C1 Turkic (negative-aorist family + patronymic)
    "escu",
    "eanu",  # B2 Romanian (RO -> B2 in this taxonomy)
    "ovic",
    "evic",  # B2 ASCII South-Slavic patronymics
    "idis",
    "iadis",  # B3 Greek patronymics (R59.4)
    "nezhad",  # C2 Persian — romanization twin of 'nejad' (R59.4)
    "dottir",  # A3 Icelandic patronymic, ASCII form (R59.4)
}

# Tier 2: Medium suffixes — fire GROUP by themselves, need corroboration for LEAF.
# Longer, more specific suffixes that ARE diagnostic for a leaf.
MEDIUM_SUFFIXES_TO_LEAF = {
    # Slavic Central (B2) — Polish/Czech
    "owski": "B2",
    "ewski": "B2",
    "inski": "B2",
    "anski": "B2",
    "wicz": "B2",
    # Slavic East (B1) — Russian
    "evsky": "B1",
    "ovsky": "B1",
    "insky": "B1",
    # Baltic (C9) — Lithuanian
    "auskas": "C9",
    "aitis": "C9",
    "evicius": "C9",
    # R59.5: raw-diacritic form only — the folded 'icius' would collide
    # with the Latin-humanist class (Fabricius, A2/A3 bearers); 'ičius'
    # with the háček is Lithuanian-specific (Čekanavičius, adjudicated).
    # Recovers part of the coverage retired with the anchorless
    # permitted-set license.
    "ičius": "C9",
}

# Bare short suffixes that only fire a GROUP, never a leaf alone.
MEDIUM_SUFFIXES_TO_GROUP = {
    "ski": "SLAVIC_CENTRAL",
    "sky": "SLAVIC_EAST",
    "ou": "HELLENIC",
    "is": "HELLENIC",
}

MEDIUM_SUFFIX_WEIGHT_GROUP = 1.2  # weight for group-level boost
MEDIUM_SUFFIX_WEIGHT_LEAF = 1.0  # additional weight if corroborated

# Hispanic surnames shared between A1 (diaspora) and G1 (Latin American).
# These bypass surname exact-match to let the scorer evaluate given-name evidence.
_HISPANIC_SHARED_SURNAMES = {
    "garcia",
    "rodriguez",
    "martinez",
    "hernandez",
    "lopez",
    "gonzalez",
    "perez",
    "sanchez",
    "ramirez",
    "torres",
    "flores",
    "rivera",
    "gomez",
    "diaz",
    "cruz",
    "morales",
    "reyes",
    "gutierrez",
    "ortiz",
}

REGION_GROUPS = {
    "ANGLO_SPHERE": ["A1"],
    "GERMANIC_WESTERN": ["A2"],
    "NORDIC_BALTIC": ["A3"],
    "OCEANIA_PACIFIC": ["A4"],
    "CARIBBEAN_FRENCH": ["A5"],
    "SLAVIC_EAST": ["B1"],
    "SLAVIC_CENTRAL": ["B2"],
    "HELLENIC": ["B3"],
    "TURKIC": ["C1"],
    "BALTIC": ["C9"],
    "PERSIAN": ["C2"],
    "ARABIC": ["C3", "C4", "C5"],
    "HEBREW": ["C6"],
    "ARMENIAN": ["C7"],
    "GEORGIAN": ["C8"],
    "SOUTH_ASIAN": ["D1", "D2", "D3", "D4", "D5"],
    "SINOPHONE": ["E1", "E2"],
    "JAPANESE": ["E3"],
    "KOREAN": ["E4"],
    "VIETNAMESE": ["E5"],
    "SEA": ["E6", "E7"],
    "SSA": ["F1", "F2", "F3", "F4"],
    "LATIN_AMERICAN": ["G1"],
}
LEAF_TO_GROUP = {leaf: g for g, leaves in REGION_GROUPS.items() for leaf in leaves}

_MEDIUM = {
    "E1": {"surnames": {"sun", "zhou", "gao", "wu", "xu", "zhu", "deng", "mao", "cai"}},
    "E4": {"surnames": {"han", "oh", "ryu", "yoon", "ahn"}},
    "D1": {"surnames": {"singh", "kumar", "patel", "agrawal", "agarwal", "sreenadh"}},
    "A1": {
        "surnames": {
            "grant",
            "ferguson",
            "wallace",
            "west",
            "cole",
            "hawkins",
            "oliver",
        },
        # Hispanic surnames common in USA (diaspora) - lower weight than G1
        "hispanic_diaspora": {
            "garcia",
            "rodriguez",
            "martinez",
            "lopez",
            "hernandez",
            "gonzalez",
            "perez",
            "sanchez",
            "ramirez",
            "torres",
            "flores",
            "rivera",
            "gomez",
            "diaz",
        },
    },
    "A2": {
        "particles": {"de", "del", "van", "von", "da", "di", "du", "la", "le"},
        "surnames": {"haas", "hahn", "kurz", "lang", "moser", "pohl", "roth", "sauer"},
    },
    "G1": {
        # Shared Lusophone surnames (demoted from _STRONG to _MEDIUM)
        "surnames": {
            "silva",
            "santos",
            "oliveira",
            "souza",
            "costa",
            "ferreira",
            "alves",
            "pereira",
            "lopes",
        },
    },
    "A3": {
        "surnames": {"berg", "lund", "dahl", "holmberg", "strand", "lindqvist", "holm"}
    },
    "B1": {"surnames": {"ivanov", "petrov", "sokolov"}},
    "B2": {
        "surnames": {
            "król",
            "wieczorek",
            "dudek",
            "zając",
            "krejčí",
            "růžička",
            "beneš",
        }
    },
}

# Diaspora down-weights (region, surname: multiplier in scoring)
# Lower values mean "this surname is less indicative of this region"
_DIASPORA_DOWNWEIGHT = {
    # South Asian surnames in Western contexts
    ("A2", "singh"): 0.5,  # 'singh' in A2 should not outrank D1
    ("A1", "singh"): 0.4,
    ("A2", "bal"): 0.6,
    # Hispanic surnames in non-Hispanic regions (due to diaspora/colonization)
    ("A1", "garcia"): 0.6,  # Hispanic in USA → prefer G1
    ("A1", "rodriguez"): 0.6,
    ("A1", "martinez"): 0.6,
    ("A1", "lopez"): 0.6,
    ("A1", "hernandez"): 0.6,
    ("E7", "garcia"): 0.7,  # Spanish colonial influence in Philippines
    ("E7", "rodriguez"): 0.7,
    ("E7", "martinez"): 0.7,
    ("F4", "garcia"): 0.7,  # Spanish names in Lusophone Africa
    ("F4", "rodriguez"): 0.7,
}

# Build reverse index: given name → set of regions that contain it
# Used for ambiguity weighting (IDF-like)
from collections import defaultdict as _defaultdict

_GIVEN_TO_REGIONS = _defaultdict(set)
for _region_code, _patterns in _STRONG.items():
    for _g in _patterns.get("given_frag", set()):
        _GIVEN_TO_REGIONS[_g].add(_region_code)


# Load learned features (auto-mined from labeled corpus)
_LEARNED_FEATURES = None


def _load_learned_features():
    global _LEARNED_FEATURES
    if _LEARNED_FEATURES is not None:
        return _LEARNED_FEATURES
    path = Path(__file__).parent.parent.parent / "config" / "learned_features.json"
    if path.exists():
        try:
            import json

            with open(path) as f:
                _LEARNED_FEATURES = json.load(f)
            logger.info(
                f"Loaded {len(_LEARNED_FEATURES.get('surnames', {}))} learned surname features"
            )
        except Exception as e:
            logger.warning(f"Failed to load learned features: {e}")
            _LEARNED_FEATURES = {}
    else:
        _LEARNED_FEATURES = {}
    return _LEARNED_FEATURES


def _score_priority_rules(name, possible):
    """
    Returns (region, confidence, debug) using priority lexicons.
    Confidence is 0.60–0.90 depending on strength/co-occurrence.

    Set REGION_RULES_VERBOSE=1 to include detailed scoring audit trail in metadata.
    """
    import os

    verbose = os.getenv("REGION_RULES_VERBOSE", "0") == "1"

    tokens = _latin_tokens(name)
    if not tokens:
        return (None, 0.0, {"reason": "no_tokens"})
    set(tokens)
    name_l = " ".join(tokens)

    # R58.8: raw (unfolded) view of the name for diacritic-aware rules —
    # _latin_tokens NFKD-folds to ASCII, which destroyed every non-ASCII
    # suffix rule and every orthographic guard. NFC keeps the marks.
    _raw_name = unicodedata.normalize("NFC", name).lower()
    _raw_tokens = _WORD.findall(_raw_name)
    # Definitive Turkic orthography (dotless ı, ş, ğ — no Spanish use).
    _raw_turkic_marked = any(c in "ışğ" for c in _raw_name)

    # Build set of ALL known given name fragments across all regions
    # Used to prevent matching given names as surnames
    all_given_frags = set()
    all_surname_suffixes = set()
    for region_patterns in _STRONG.values():
        all_given_frags.update(region_patterns.get("given_frag", set()))
        all_surname_suffixes.update(region_patterns.get("surname_suffix", set()))

    # Helper: Check if token should be filtered as a given name
    # Only filter if: (1) exact match, OR (2) starts with long (4+) fragment
    # BUT: never filter if token ends with a known surname suffix
    # (prevents "ivanishvili" being classified as given name due to "ivan" prefix
    #  when it actually ends with Georgian "-shvili" suffix)
    def is_given_name(tok):
        # If token matches a LONG surname suffix (4+ chars), it's likely a surname
        # Short suffixes like -is, -ov, -in are too common to override given name status
        # (prevents "luis" being kept as surname due to Greek -is suffix)
        for suf in all_surname_suffixes:
            if tok.endswith(suf) and len(suf) >= 4 and len(tok) > len(suf) + 1:
                return False
        for g in all_given_frags:
            if tok == g:  # Exact match
                return True
            if len(g) >= 4 and tok.startswith(g):  # Long fragment
                return True
        return False

    # R58.8 (adversarial verification): when the name carries a comma, the
    # surname position is DECLARED — only pre-comma tokens are surname
    # candidates. Previously given-name tokens were scored against other
    # regions' STRONG surname lexicons and won: 'Mahler, Kurt' -> C1
    # [STRONG_SURNAME:kurt:5.00], 'Bortolotti, Carlos Eduardo' -> F4
    # [STRONG_SURNAME:eduardo:5.00].
    _comma_candidates = None
    if "," in name:
        _pre = _latin_tokens(name.split(",", 1)[0])
        if _pre:
            _comma_candidates = _pre

    # For surname matching: check first and last tokens, but skip known given names
    # - Western names: surname is LAST token (e.g., "Antonio Fernández")
    # - CJK names: surname is FIRST token (e.g., "Zhao Min")
    # - Skip middle tokens (typically given names)
    if _comma_candidates is not None:
        surname_candidates = _comma_candidates
    elif len(tokens) == 1:
        surname_candidates = tokens
    elif len(tokens) == 2:
        # For 2-token names: check both, but filter out known given names
        surname_candidates = [tok for tok in tokens if not is_given_name(tok)]
        if not surname_candidates:
            # If both are given names, fall back to checking both (rare edge case)
            surname_candidates = tokens
    else:
        # 3+ tokens: check first (CJK) and last 2 (Western compound surnames), skip middle
        surname_candidates = [
            tok for tok in [tokens[0]] + tokens[-2:] if not is_given_name(tok)
        ]
        if not surname_candidates:
            surname_candidates = [tokens[0]] + tokens[-2:]

    surname_tokens_str = " ".join(surname_candidates)

    surname_scores: dict[str, float] = {r: 0.0 for r in possible}
    given_scores: dict[str, float] = {r: 0.0 for r in possible}
    reasons: dict[str, list[str]] = {r: [] for r in possible}

    for r in possible:
        strong = _STRONG.get(r, {})
        medium = _MEDIUM.get(r, {})

        # Strong: exact surname hit (word-boundary)
        # FIXED: Check surname candidates (first/last), excluding known given names
        for s in strong.get("surnames", set()):
            if _wb(s).search(surname_tokens_str):
                w = 5.0
                w *= _DIASPORA_DOWNWEIGHT.get((r, s), 1.0)
                surname_scores[r] += w
                reasons[r].append(f"STRONG_SURNAME:{s}:{w:.2f}")

        # Strong: given name fragment (prefix/fragment, not substring anywhere)
        # ONLY match in non-surname tokens to prevent "ivanishvili" matching "ivan"
        given_check_tokens = [tok for tok in tokens if tok not in surname_candidates]
        if not given_check_tokens:
            # Single-token names: skip given name matching entirely
            given_check_tokens = []
        for g in strong.get("given_frag", set()):
            matched = False
            for tok in given_check_tokens:
                if tok == g:
                    matched = True
                    break
                # Also match exact hyphen-parts: "jae-in" matches "jae" and "in"
                if "-" in tok:
                    for part in tok.split("-"):
                        if part == g:
                            matched = True
                            break
                if matched:
                    break
            if matched and tok not in strong.get("surnames", set()):
                # Ambiguity weighting: names appearing in many regions get lower weight
                ambiguity = len(_GIVEN_TO_REGIONS.get(g, {r}))
                if ambiguity >= 4:
                    continue  # too ambiguous across regions, skip
                w = 2.0 / ambiguity
                given_scores[r] += w
                reasons[r].append(f"STRONG_GIVEN:{g}:{w:.2f}")

        # Strong: hyphenated given for Korean
        if strong.get("hyphen_given") and any("-" in tok for tok in tokens):
            given_scores[r] += 2.5
            reasons[r].append("STRONG_HYPHEN_GIVEN:2.50")

        # Strong: suffix patterns (Persian/Japanese/Slavic/Nordic/etc.)
        # ONLY check surname candidates, not given names
        # (prevents "luis" matching Greek -is suffix)
        for suf in strong.get("surname_suffix", set()):
            # R58.8: the Hispanic -ez/-az/-iz/-oz rule fired on the commonest
            # Turkish surnames (Yılmaz -> G1@0.85). Two guards, both from
            # verified counterexamples: (1) definitive Turkic orthography
            # anywhere in the raw name (dotless ı, ş, ğ — no Spanish use)
            # kills the Hispanic suffix; (2) tokens ending -maz/-mez (the
            # Turkish negative-aorist surname family: Yılmaz, Sönmez,
            # Korkmaz, Söylemez) never count for it.
            if suf in ("ez", "az", "iz", "oz"):
                if _raw_turkic_marked:
                    continue
                cand = [
                    t
                    for t in surname_candidates
                    if not (t.endswith("maz") or t.endswith("mez"))
                ]
            elif suf in ("maz", "mez"):
                # C1 Turkish negative-aorist family. Three guards, all from
                # verified counterexamples (see the C1 table comment):
                # consonant before the suffix (Gómez/Gámez/Jaimez/Tomaz/
                # Grumaz all have a vowel there; Söylemez-type vowel-stem
                # Turkish names are sacrificed to abstention), length >= 6
                # (drops Almaz/Elmaz/Ölmez, the short-stem collision zone),
                # curated exclusion 'gormaz' (Spanish toponymic surname).
                cand = [
                    t
                    for t in surname_candidates
                    if len(t) >= 6 and t != "gormaz" and t[-4] not in "aeiou"
                ]
            elif suf == "escu":
                # Romanian -escu. 'francescu' is the Corsican given name.
                cand = [
                    t for t in surname_candidates if len(t) > 5 and t != "francescu"
                ]
            elif suf in ("ovic", "evic"):
                # ASCII South-Slavic patronymic. When the raw name carries
                # the diacritic form the raw-token rules (ović/ević) own the
                # match — skip to avoid double-counting; Belarusian Łacinka
                # (-evič/-ovič) is NOT B2, so it abstains rather than fires.
                # 'ludovic' is a French given name, never a Slavic surname.
                if any(
                    rt.endswith(("ović", "ević", "ovič", "evič")) for rt in _raw_tokens
                ):
                    cand = []
                else:
                    cand = [
                        t for t in surname_candidates if len(t) > 5 and t != "ludovic"
                    ]
            elif suf == "oglu":
                # Turkish patronymic — but Anatolian-Greek families carry
                # ASCII -oglu too (adjudicated counterexample: 'Papasoglu,
                # Panos' -> B3 on the 843 benchmark; Greek renderings are
                # usually -oglou, yet bare -oglu occurs). The bare ASCII
                # form therefore needs TURKIC corroboration: definitive
                # Turkic orthography anywhere in the raw name (ı/ş/ğ, or
                # ö/ü/ç which Greek romanizations never carry), or a C1
                # given-name hit (the given loop above has already run for
                # this region). Uncorroborated -oglu abstains.
                _turkic_corroborated = (
                    _raw_turkic_marked
                    or any(c in "öüç" for c in _raw_name)
                    or any("STRONG_GIVEN" in x for x in reasons[r])
                )
                if _turkic_corroborated:
                    cand = [t for t in surname_candidates if len(t) > len(suf) + 1]
                else:
                    cand = []
            elif suf == "eanu":
                cand = [t for t in surname_candidates if len(t) > len(suf) + 1]
            elif suf in ("idis", "iadis"):
                # R59.4 Greek patronymic suffixes. Curated exclusions from
                # verified non-Greek bearers: 'davidis' (Latin/German form
                # of David), 'aidis'/'naidis' (Lithuanian). Length guard
                # keeps the bare token from matching itself.
                cand = [
                    t
                    for t in surname_candidates
                    if len(t) > len(suf) + 1 and t not in ("davidis", "aidis", "naidis")
                ]
            elif suf == "sson":
                # R59.4 curated exclusions — non-Nordic -sson surnames that
                # cannot claim a single leaf: 'frasson' (Italian A2 /
                # Brazilian G1 bearers), 'masson' (dual etymology: French
                # Masson AND Scottish Mass-son, live corpus bearers on both
                # sides), 'wasson' (no named corpus bearer to back a YAML
                # claim). These abstain. The other verified non-Nordic
                # -sson names (Besson, Casson, Mathisson, Malbouisson…)
                # are claimed upstream by curated surname_exact YAML
                # entries, each backed by a named corpus bearer.
                cand = [
                    t
                    for t in surname_candidates
                    if t not in ("frasson", "masson", "wasson")
                ]
            elif suf == "dottir":
                # R59.4 ASCII Icelandic patronymic: real bearers always
                # carry a stem (Óladóttir -> 'oladottir'); a bare 'Dottir'
                # surname does not exist and must not self-match.
                cand = [t for t in surname_candidates if len(t) > len(suf) + 1]
            else:
                cand = surname_candidates
            # R58.8: non-ASCII suffixes ('ová', 'ský', 'ović'…) were DEAD
            # CODE — tokens are NFKD-folded to ASCII before matching, so
            # e.g. B2's 'ová' never matched and Czech feminine surnames fell
            # to B1's 'ova' (Svobodová -> B1/SLAVIC_EAST). Match non-ASCII
            # suffixes against the RAW (unfolded) tokens; and the B1 'ova'
            # rule skips names whose raw form carries the diacritic feminine
            # 'ová' (the diacritic IS the Czech/Slovak-vs-East-Slavic
            # disambiguator).
            if not suf.isascii():
                hit = any(rt.endswith(suf) for rt in _raw_tokens)
            elif suf == "ova" and any(rt.endswith("ová") for rt in _raw_tokens):
                hit = False
            else:
                hit = any(tok.endswith(suf) for tok in cand)
            if hit:
                w = 2.5
                if suf == "ian":
                    w = 1.5  # ambiguous with Armenian
                surname_scores[r] += w
                reasons[r].append(f"STRONG_SURNAME_SUFFIX:{suf}:{w:.2f}")

        # Strong: prefix patterns (Irish O', Scottish Mac/Mc, Anglo-Norman Fitz)
        for pfx in strong.get("surname_prefix", set()):
            # R58.8: a bare token EQUAL to the prefix is a given name, not a
            # prefixed surname ('Bratteli Ola' fired F2's ola- prefix on the
            # given name Ola; Oladipo/Olawale still match). R59.4: tokens
            # ending -dottir are Icelandic patronymics, never Yoruba
            # ('Oladottir' = Óladóttir, daughter of Óli — fired F2 wrongly).
            if any(
                tok.startswith(pfx)
                and len(tok) > len(pfx) + 1
                and not tok.endswith("dottir")
                for tok in surname_candidates
            ):
                surname_scores[r] += 3.0
                reasons[r].append(f"STRONG_SURNAME_PREFIX:{pfx}:3.00")

        for suf in strong.get("given_suffix", set()):
            if any(tok.endswith(suf) for tok in tokens):
                given_scores[r] += 2.0
                reasons[r].append(f"STRONG_GIVEN_SUFFIX:{suf}:2.00")

        # Strong: particles (de, van, von, saint, etc.)
        for p in strong.get("particles", set()):
            if _wb(p).search(name_l):
                surname_scores[r] += 2.0
                reasons[r].append(f"STRONG_PARTICLE:{p}:2.00")

        # Medium indicators
        # FIXED: Check surname candidates (first/last), excluding known given names
        for s in medium.get("surnames", set()):
            if _wb(s).search(surname_tokens_str):
                surname_scores[r] += 1.5
                reasons[r].append(f"MEDIUM_SURNAME:{s}:1.50")
        for p in medium.get("particles", set()):
            if _wb(p).search(name_l):
                surname_scores[r] += 0.8
                reasons[r].append(f"MEDIUM_PARTICLE:{p}:0.80")

        # Hispanic diaspora surnames (for A1) - even lower weight
        # FIXED: Check surname candidates (first/last), excluding known given names
        for s in medium.get("hispanic_diaspora", set()):
            if _wb(s).search(surname_tokens_str):
                surname_scores[r] += 1.0
                reasons[r].append(f"MEDIUM_HISPANIC_DIASPORA:{s}:1.00")

        # Combination bonus: given+surname co-occurrence (all regions with both patterns)
        # This helps disambiguate diaspora cases (e.g., "Linda Garcia" = A1 not G1)
        if strong.get("given_frag"):
            # Check for surname match (STRONG, MEDIUM, or hispanic_diaspora)
            # FIXED: Check surname candidates (first/last), excluding known given names
            has_surname = (
                any(tok in strong.get("surnames", set()) for tok in surname_candidates)
                or any(
                    _wb(tok).search(surname_tokens_str)
                    for tok in medium.get("surnames", set())
                )
                or any(
                    _wb(tok).search(surname_tokens_str)
                    for tok in medium.get("hispanic_diaspora", set())
                )
            )
            # Check for given match, but exclude tokens that are exact surname matches
            has_given = any(
                any(
                    tok.startswith(g) and tok not in strong.get("surnames", set())
                    for tok in tokens
                )
                for g in strong.get("given_frag", set())
            )
            if has_surname and has_given:
                surname_scores[r] += 2.0
                reasons[r].append("COMBO_GIVEN_SURNAME:2.00")

    # ── Medium suffix tier (Tier 2) ──
    # Fires group (1.2) by itself. Fires leaf (+1.0) only if corroborated later.
    medium_leaf_hits = {}  # {leaf: [token, ...]} for later corroboration check
    for tok in surname_candidates:
        # Skip if a signature suffix already matched this token
        if any(
            tok.endswith(sig) and len(tok) > len(sig) + 1 for sig in SIGNATURE_SUFFIXES
        ):
            continue
        # Longer medium suffixes → specific leaf hint
        matched_medium = False
        for suf, leaf in sorted(
            MEDIUM_SUFFIXES_TO_LEAF.items(), key=lambda x: -len(x[0])
        ):
            # R59.5: non-ASCII medium suffixes ('ičius') match against the
            # RAW token whose folded form is this candidate — same R58.8
            # rationale as the STRONG loop (folding destroys the mark that
            # IS the discriminator).
            if not suf.isascii():
                hit = any(
                    rt.endswith(suf)
                    and len(rt) > len(suf) + 1
                    and _latin_tokens(rt) == [tok]
                    for rt in _raw_tokens
                )
            else:
                hit = tok.endswith(suf) and len(tok) > len(suf) + 1
            if hit:
                group = LEAF_TO_GROUP.get(leaf)
                if group:
                    for r in possible:
                        if LEAF_TO_GROUP.get(r) == group:
                            surname_scores[r] += MEDIUM_SUFFIX_WEIGHT_GROUP
                            reasons[r].append(
                                f"MEDIUM_SUFFIX:{suf}:{MEDIUM_SUFFIX_WEIGHT_GROUP:.2f}"
                            )
                    medium_leaf_hits.setdefault(leaf, []).append(tok)
                matched_medium = True
                break  # longest match wins
        if not matched_medium:
            # Bare short suffixes → group only. R59.4: the bare '-is' rule
            # fired HELLENIC on Baltic/Latin-German lookalikes ('Aidis,
            # Ruta' — Lithuanian — emitted B3@0.75, a live wrong leaf);
            # same curated exclusion trio as the STRONG idis/iadis rules.
            for suf, group in MEDIUM_SUFFIXES_TO_GROUP.items():
                if suf == "is" and tok in ("davidis", "aidis", "naidis"):
                    continue
                if tok.endswith(suf) and len(tok) > len(suf) + 1:
                    for r in possible:
                        if LEAF_TO_GROUP.get(r) == group:
                            surname_scores[r] += MEDIUM_SUFFIX_WEIGHT_GROUP
                            reasons[r].append(
                                f"MEDIUM_SUFFIX_GROUP:{suf}:{MEDIUM_SUFFIX_WEIGHT_GROUP:.2f}"
                            )
                    break

    # ── Learned features pass ──
    # Only use positive (supporting) log-odds and cap total contribution
    # so learned features act as tiebreakers, not overrides of handcrafted rules.
    # Only surname exact matches and given names are used; suffix/n-gram features
    # are too noisy with a small training corpus and tend to give similar scores
    # to all regions, destroying handcrafted margins.
    learned = _load_learned_features()
    if learned and learned.get("surnames"):
        matched_handcrafted = set()  # track what handcrafted already matched
        # Collect handcrafted-matched tokens to avoid double-counting
        for r_reasons in reasons.values():
            for reason_str in r_reasons:
                if "STRONG_SURNAME:" in reason_str:
                    parts = reason_str.split(":")
                    if len(parts) >= 2:
                        matched_handcrafted.add(parts[1])

        for r in possible:
            learned_surname_bump = 0.0
            learned_given_bump = 0.0

            # Learned surname exact matches
            for tok in surname_candidates:
                if tok not in matched_handcrafted:
                    w = learned.get("surnames", {}).get(tok, {}).get(r, 0)
                    if w > 0:
                        learned_surname_bump += 0.5 * w

            # Learned suffix matches (only long suffixes 4+ chars, and only if
            # the suffix has weights for fewer than 10 regions to ensure specificity)
            learned_suffixes = learned.get("suffixes", {})
            for tok in surname_candidates:
                for suf in [tok[-n:] for n in (4, 5) if len(tok) >= n]:
                    suf_weights = learned_suffixes.get(suf, {})
                    # Only use discriminative suffixes (appear in few regions)
                    pos_regions = sum(1 for v in suf_weights.values() if v > 0)
                    if pos_regions <= 8:
                        w = suf_weights.get(r, 0)
                        if w > 0:
                            learned_surname_bump += 0.2 * w

            # Learned given name weights
            for tok in given_check_tokens:
                w = learned.get("given_names", {}).get(tok, {}).get(r, 0)
                if w > 0:
                    learned_given_bump += 0.2 * w

            # Cap learned contribution so it cannot override handcrafted signals
            # Keep caps low: learned features are tiebreakers, not primary evidence
            learned_bump_capped = min(learned_surname_bump, 0.4)
            surname_scores[r] += learned_bump_capped
            given_scores[r] += min(learned_given_bump, 0.3)

            # Medium suffix corroboration: if learned features agree with a medium
            # suffix leaf hit, promote from group to leaf
            if r in medium_leaf_hits and learned_bump_capped > 0.05:
                surname_scores[r] += MEDIUM_SUFFIX_WEIGHT_LEAF
                reasons[r].append(
                    f"MEDIUM_SUFFIX_CORROBORATED:{medium_leaf_hits[r][0]}:"
                    f"{MEDIUM_SUFFIX_WEIGHT_LEAF:.2f}"
                )

    # Medium suffix corroboration from STRONG_SURNAME matches
    for leaf, toks in medium_leaf_hits.items():
        if leaf in possible and any(
            "STRONG_SURNAME:" in r for r in reasons.get(leaf, [])
        ):
            # Already corroborated by a strong surname match
            if not any(
                "MEDIUM_SUFFIX_CORROBORATED" in r for r in reasons.get(leaf, [])
            ):
                surname_scores[leaf] += MEDIUM_SUFFIX_WEIGHT_LEAF
                reasons[leaf].append(
                    f"MEDIUM_SUFFIX_CORROBORATED:{toks[0]}:"
                    f"{MEDIUM_SUFFIX_WEIGHT_LEAF:.2f}"
                )

    # Combine channels: surnames dominate (1.0x), given names are weak tiebreakers (0.35x)
    scores = {r: 1.0 * surname_scores[r] + 0.35 * given_scores[r] for r in possible}

    # Find winner
    sorted_regions = sorted(scores.items(), key=lambda x: -x[1])
    if not sorted_regions or sorted_regions[0][1] <= 0:
        metadata = (
            {"reason": "no_signal", "scores": scores}
            if verbose
            else {"reason": "no_signal"}
        )
        return (None, 0.0, metadata)

    best_region = sorted_regions[0][0]
    best_score = sorted_regions[0][1]
    second_score = sorted_regions[1][1] if len(sorted_regions) > 1 else 0
    margin = best_score - second_score

    # Build candidates list (top-5 scored regions with positive scores)
    candidates = [[r, round(s, 3)] for r, s in sorted_regions[:5] if s > 0]

    # Mixed-name abstain: when a shared Hispanic surname appears with
    # an Anglo-identified given name, this is a genuine diaspora ambiguity.
    # Abstain with candidates rather than forcing a leaf.
    has_hispanic_surname = any(
        tok in _HISPANIC_SHARED_SURNAMES for tok in surname_candidates
    )
    has_anglo_given = any("STRONG_GIVEN" in r for r in reasons.get("A1", []))
    if (
        has_hispanic_surname
        and has_anglo_given
        and "A1" in possible
        and "G1" in possible
    ):
        return (
            None,
            0.0,
            {
                "reason": "mixed_anglo_hispanic",
                "candidates": candidates,
                "best_region": best_region,
                "group": "HISPANIC_ANGLO_MIXED",
            },
        )

    # Sovietized Turkic mixed-name rule: Slavic surname suffix (-ov/-ev)
    # with Turkic given name evidence → hybrid, abstain with candidates.
    has_slavic_surname = any(
        "STRONG_SURNAME_SUFFIX:" in r
        and any(s in r for s in ("ov:", "ev:", "enko:", "ovich:", "evich:"))
        for r in reasons.get("B1", [])
    )
    has_turkic_given = any("STRONG_GIVEN" in r for r in reasons.get("C1", []))
    # R59.2 (held-out finding: 'Rifat Jumagulov'->B1, true C1; 'Abdulkadyr
    # Buchaev'->B1, true C9): the given-lexicon check misses most Turkic/
    # Muslim given names. Two additional high-precision signals: (a) a
    # Turkic stem morpheme inside the -ov/-ev token itself (jumaGULov,
    # nurBEKov — gul/bek/bay/khan/kul are Turkic elements, not Slavic), and
    # (b) an Abdul-/Magomed-class given token. Russian names (Nikolaev,
    # Ivanov) carry neither and stay B1.
    _TURKIC_STEMS = ("gul", "bek", "bay", "khan", "kul")
    turkic_stem = any(
        (tok.endswith("ov") or tok.endswith("ev"))
        and any(mrk in tok[:-2] for mrk in _TURKIC_STEMS)
        for tok in surname_candidates
    )
    muslim_given = any(
        tok.startswith(("abdul", "abdel", "magomed", "muhamm", "mohamm"))
        for tok in tokens
    )
    if (
        has_slavic_surname
        and (has_turkic_given or turkic_stem or muslim_given)
        and best_region == "B1"
        and ("C1" in possible or "C9" in possible)
    ):
        return (
            None,
            0.0,
            {
                "reason": "sovietized_turkic",
                "candidates": candidates,
                "best_region": best_region,
                "group": "SOVIETIZED_TURKIC_MIXED",
            },
        )

    # Expert rule: given-name-only evidence NEVER produces leaf prediction
    best_surname = surname_scores.get(best_region, 0)
    best_given = given_scores.get(best_region, 0)
    if best_surname <= 0 and best_given > 0:
        group = LEAF_TO_GROUP.get(best_region)
        return (
            None,
            0.0,
            {
                "reason": "given_only_no_surname",
                "best_region": best_region,
                "group": group,
                "given_score": best_given,
                "candidates": candidates,
            },
        )

    # Abstain if evidence is too weak or margin too small.
    # Thresholds default to production values (expert-validated on the
    # 523-entry adjudicated benchmark). Overridable for RC-curve sweeps
    # via tools/rc_curve.py without code changes.
    _min_score = float(os.getenv("GMNAP_SCORER_MIN_SCORE", "0.5"))
    _min_margin = float(os.getenv("GMNAP_SCORER_MIN_MARGIN", "0.3"))
    if best_score < _min_score or margin < _min_margin:
        return (
            None,
            0.0,
            {
                "reason": "low_score_or_margin",
                "best_score": best_score,
                "margin": margin,
                "best_region": best_region,
                "group": LEAF_TO_GROUP.get(best_region),
                "candidates": candidates,
            },
        )

    # Calibrate confidence
    conf = 0.60 + min(0.30, (best_score / (best_score + 5.0)) * 0.30)

    # Build metadata (verbose mode includes full audit trail)
    debug = {
        "reasons": reasons.get(best_region, []),
        "best_score": best_score,
        "margin": margin,
        "surname_score": surname_scores.get(best_region, 0),
        "given_score": given_scores.get(best_region, 0),
        "candidates": candidates,
    }
    if verbose:
        debug["all_scores"] = scores
        debug["all_reasons"] = {k: v for k, v in reasons.items() if v}
        debug["tokens"] = tokens
        debug["name_normalized"] = name_l

    return (best_region, conf, debug)


def _nudge_by_doi_affiliation(entry, region, conf) -> float:
    """Minimal DOI/affiliation priority nudge (costs near-zero runtime)."""
    doi = (entry.get("DOI") or "").lower()
    aff = (entry.get("Affiliation") or "").lower()
    bump = 0.0
    if doi.startswith("10.1145") and region in ("A1", "A2"):
        bump += 0.02
    if "univ" in aff or "institute" in aff or "department" in aff:
        bump += 0.02
    return min(0.95, conf + bump)
