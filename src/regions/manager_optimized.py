"""
Optimized Region detection and management for GMNAP.
Performance improvements:
1. Singleton pattern for FastText model loading
2. Lazy loading of regions only when needed
3. Cache region detection results
4. Only load regions that are actually implemented
"""

# Marker so pipeline can assert correct class is wired (prevents wrong-file regression)
_V7_OPTIMIZED = True

import logging
import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

# Initialize logger first
logger = logging.getLogger(__name__)

# Try to import fasttext, but make it optional for Docker builds
try:
    import warnings

    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", message=".*load_model does not return.*")
        import fasttext
    FASTTEXT_AVAILABLE = True
except ImportError:
    FASTTEXT_AVAILABLE = False
    logger.warning(
        "fasttext not available - ML detection disabled, using rules-based detection only"
    )

from src.core.cache.sized_lru import SizedLRU
from src.core.security_validator import SecurityError, SecurityValidator
from src.core.unicode_handler import UnicodeNormalizer

from .base import REGION_CODES, RegionSpec, get_region_for_territory

# Token extraction and word-boundary utilities for systematic pattern matching
_WORD = re.compile(
    r"[A-Za-zÀ-ÖØ-öø-ÿ]+(?:['-][A-Za-zÀ-ÖØ-öø-ÿ]+)*"
)  # token incl. hyphenated (jae-in) and apostrophe (o'brien, o'sullivan)


def _latin_tokens(name: str) -> list[str]:
    """Extract tokens from name, normalized and lowercased."""
    name_nfkd = unicodedata.normalize("NFKD", name).lower()
    name_ascii = "".join(ch for ch in name_nfkd if ch.isalnum() or ch in "- '")
    return _WORD.findall(name_ascii)


def _wb(pattern: str) -> re.Pattern:
    """Whole word or hyphen-bounded pattern (e.g. 'Jae-in', 'Min-soo')."""
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
        },
    },
    "A2": {  # Western Europe (German, French, Italian, Dutch, Belgian, Swiss, Austrian)
        "surname_suffix": {
            "mann",
            "hofer",
            "stein",
            "berg",
            "feld",
            "schmidt",
            "schneider",
            "ato",
            "ini",
            "elli",
            "otti",
            "ucci",
            "acci",
            "ovena",
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
        },
    },
    "A3": {  # Nordic-Baltic (Sweden, Norway, Denmark, Finland, Iceland, Baltic states)
        "surname_suffix": {"son", "sen", "sson", "sdóttir", "sdotter"},
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
            "enko",
            "ski",
            "sky",
            "skaya",
            "ovski",
            "ovsky",
            "evich",
            "ovich",
            "yn",
            "yev",
            "in",
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
            "ski",
            "ska",
            "cki",
            "cka",
            "wicz",
            "wski",
            "owski",
            "ewski",
            "ová",
            "ský",
            "ček",
            "ek",
            "ák",
            "ić",
            "ović",
            "ević",
            "vić",
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
        "surname_suffix": {"os", "as", "is", "ou", "poulos", "akis", "opoulos", "ides"},
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
            "timur",
            "ruslan",
            "alisher",
            "bekzod",
        },
    },
    "C2": {  # Persian-Tajik
        "surname_suffix": {"zadeh", "pour", "nejad", "nouri", "ighi", "ani"},
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
        "surname_suffix": {"dze", "shvili", "adze", "ia", "ani", "uri"},
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
    "C9": {  # Caucasus Turkic (Azeri, Kumyk, Nogai)
        "surnames": {
            "aliyev",
            "hasanov",
            "mammadov",
            "huseynov",
            "ismailov",
            "rahimov",
            "abbasov",
            "karimov",
            "ibrahimov",
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
            "eldar",
            "javid",
            "rashad",
            "samir",
            "vugar",
            "tural",
            "farid",
            "aysel",
            "gunay",
            "leyla",
            "nigar",
            "sevinj",
            "narmin",
            "aytan",
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
            "dan",
            "paul",
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
            "pang",
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
        "surname_suffix": {"moto", "kawa", "zaki", "hara", "mura", "yama", "da", "ta"},
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
            "lim",
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
            "son",
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
    "F1": {  # SSA Francophone (Senegal, Mali, Burkina Faso, Côte d'Ivoire, etc.)
        "surnames": {
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
        },
    },
    "F2": {  # SSA Anglophone (Nigeria, Ghana, Kenya, Uganda, Tanzania, Zimbabwe)
        "surnames": {
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
            "solomon",
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
            "manuel",
            "antonio",
            "jose",
            "francisco",
            "eduardo",
            "carlos",
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
        "surname_suffix": {"ez", "az", "iz", "oz", "es", "os"},
        "surnames": {
            "garcia",
            "rodriguez",
            "martinez",
            "lopez",
            "roman",
            "hernandez",
            "gonzález",
            "pérez",
            "sánchez",
            "ramírez",
            "torres",
            "flores",
            "rivera",
            "gómez",
            "díaz",
            "cruz",
            "morales",
            "reyes",
            "gutiérrez",
            "ortiz",
            "mendoza",
            "silva",
            "santos",
            "oliveira",
            "souza",
            "costa",
            "ferreira",
            "alves",
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


def _score_priority_rules(
    name: str, possible: list[str]
) -> tuple[str | None, float, dict]:
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

    # For surname matching: check first and last tokens, but skip known given names
    # - Western names: surname is LAST token (e.g., "Antonio Fernández")
    # - CJK names: surname is FIRST token (e.g., "Zhao Min")
    # - Skip middle tokens (typically given names)
    if len(tokens) == 1:
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
            tok for tok in ([tokens[0]] + tokens[-2:]) if not is_given_name(tok)
        ]
        if not surname_candidates:
            surname_candidates = [tokens[0]] + tokens[-2:]

    surname_tokens_str = " ".join(surname_candidates)

    scores: dict[str, float] = {r: 0.0 for r in possible}
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
                scores[r] += w
                reasons[r].append(f"STRONG_SURNAME:{s}:{w:.2f}")

        # Strong: given name fragment (prefix/fragment, not substring anywhere)
        # ONLY match in non-surname tokens to prevent "ivanishvili" matching "ivan"
        given_check_tokens = [tok for tok in tokens if tok not in surname_candidates]
        if not given_check_tokens:
            # Single-token names: skip given name matching entirely
            given_check_tokens = []
        for g in strong.get("given_frag", set()):
            matched_tokens = [
                tok
                for tok in given_check_tokens
                if tok.startswith(g) and tok not in strong.get("surnames", set())
            ]
            if matched_tokens:
                scores[r] += 3.0
                reasons[r].append(f"STRONG_GIVEN:{g}:3.00")

        # Strong: hyphenated given for Korean
        if strong.get("hyphen_given") and any("-" in tok for tok in tokens):
            scores[r] += 2.5
            reasons[r].append("STRONG_HYPHEN_GIVEN:2.50")

        # Strong: suffix patterns (Persian/Japanese/Slavic/Nordic/etc.)
        # ONLY check surname candidates, not given names
        # (prevents "luis" matching Greek -is suffix)
        for suf in strong.get("surname_suffix", set()):
            if any(tok.endswith(suf) for tok in surname_candidates):
                w = 2.5
                if suf == "ian":
                    w = 1.5  # ambiguous with Armenian
                scores[r] += w
                reasons[r].append(f"STRONG_SURNAME_SUFFIX:{suf}:{w:.2f}")

        # Strong: prefix patterns (Irish O', Scottish Mac/Mc, Anglo-Norman Fitz)
        for pfx in strong.get("surname_prefix", set()):
            if any(tok.startswith(pfx) for tok in surname_candidates):
                scores[r] += 3.0
                reasons[r].append(f"STRONG_SURNAME_PREFIX:{pfx}:3.00")

        for suf in strong.get("given_suffix", set()):
            if any(tok.endswith(suf) for tok in tokens):
                scores[r] += 2.0
                reasons[r].append(f"STRONG_GIVEN_SUFFIX:{suf}:2.00")

        # Strong: prefix patterns (Arabic al-, el-, ben-, bou-)
        for pref in strong.get("surname_prefix", set()):
            if any(tok.startswith(pref) for tok in tokens):
                scores[r] += 3.0
                reasons[r].append(f"STRONG_SURNAME_PREFIX:{pref}:3.00")

        # Strong: particles (de, van, von, saint, etc.)
        for p in strong.get("particles", set()):
            if _wb(p).search(name_l):
                scores[r] += 2.0
                reasons[r].append(f"STRONG_PARTICLE:{p}:2.00")

        # Medium indicators
        # FIXED: Check surname candidates (first/last), excluding known given names
        for s in medium.get("surnames", set()):
            if _wb(s).search(surname_tokens_str):
                scores[r] += 1.5
                reasons[r].append(f"MEDIUM_SURNAME:{s}:1.50")
        for p in medium.get("particles", set()):
            if _wb(p).search(name_l):
                scores[r] += 0.8
                reasons[r].append(f"MEDIUM_PARTICLE:{p}:0.80")

        # Hispanic diaspora surnames (for A1) - even lower weight
        # FIXED: Check surname candidates (first/last), excluding known given names
        for s in medium.get("hispanic_diaspora", set()):
            if _wb(s).search(surname_tokens_str):
                scores[r] += 1.0
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
                scores[r] += 2.0
                reasons[r].append("COMBO_GIVEN_SURNAME:2.00")

    # Normalize by candidate count to avoid 'larger DB wins' artifact
    if scores:
        mx = max(scores.values())
        if mx <= 0:
            metadata = (
                {"reason": "no_signal", "scores": scores}
                if verbose
                else {"reason": "no_signal"}
            )
            return (None, 0.0, metadata)
        # Winner and calibrated confidence
        winner = max(scores.items(), key=lambda kv: kv[1])[0]
        # Map score to 0.60–0.90 band
        conf = 0.60 + min(0.30, (scores[winner] / (scores[winner] + 5.0)) * 0.30)

        # Build metadata (verbose mode includes full audit trail)
        metadata = {"reasons": reasons[winner]}
        if verbose:
            metadata["all_scores"] = scores
            metadata["all_reasons"] = {k: v for k, v in reasons.items() if v}
            metadata["tokens"] = tokens
            metadata["name_normalized"] = name_l

        return (winner, conf, metadata)
    return (None, 0.0, {"reason": "no_scores"})


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


# Singleton for FastText model to prevent multiple loads
_fasttext_model = None
_fasttext_load_attempted = False


def get_fasttext_model(config_dir: Path = Path("./config")):
    """Get or load the FastText model (singleton pattern)."""
    global _fasttext_model, _fasttext_load_attempted

    if _fasttext_model is not None:
        return _fasttext_model

    if _fasttext_load_attempted:
        # Already tried and failed, don't try again
        return None

    _fasttext_load_attempted = True

    try:
        # Try config directory first
        model_path = config_dir / "lid.176.bin"

        # Fallback to global cache directory for tests
        if not model_path.exists():
            global_model_path = Path("cache/config/lid.176.bin")
            if global_model_path.exists():
                model_path = global_model_path

        if model_path.exists():
            # Suppress fasttext C++ warning by redirecting stderr
            import os
            import sys

            old_stderr = sys.stderr
            try:
                # Redirect stderr to devnull during load
                sys.stderr = open(os.devnull, "w")
                _fasttext_model = fasttext.load_model(str(model_path))
            finally:
                sys.stderr.close()
                sys.stderr = old_stderr
            logger.info(f"Loaded FastText language detector from {model_path}")
            return _fasttext_model
        else:
            logger.warning(f"FastText model not found at {model_path}")
            return None
    except Exception as e:
        logger.error(f"Failed to load language detector: {e}")
        return None


@dataclass
class RegionDetectionResult:
    """Result of region detection."""

    region_code: str
    confidence: float
    detection_method: str
    metadata: Dict[str, Any] = field(default_factory=dict)


class RegionManager:
    """
    Optimized region detection and routing manager.

    Key optimizations:
    1. Singleton FastText model loading
    2. Lazy region loading
    3. Detection result caching
    4. Only load actually implemented regions
    """

    # Marker so pipeline can assert correct class is wired (prevents wrong-file regression)
    _V7_OPTIMIZED = True

    # List of actually implemented regions (all V7 regions with processor.py files)
    IMPLEMENTED_REGIONS = {
        # A-groups (Anglo-sphere/Western)
        "A1",
        "A2",
        "A3",
        "A4",
        "A5",
        # B-groups (Slavic)
        "B1",
        "B2",
        "B3",
        # C-groups (Middle East/Turkic)
        "C1",
        "C2",
        "C3",
        "C4",
        "C5",
        "C6",
        "C7",
        "C8",
        "C9",
        # D-groups (South Asia)
        "D1",
        "D2",
        "D3",
        "D4",
        "D5",
        # E-groups (East Asia)
        "E1",
        "E2",
        "E3",
        "E4",
        "E5",
        "E6",
        "E7",
        # F-groups (Africa)
        "F1",
        "F2",
        "F3",
        "F4",
        # G-groups (Latin America)
        "G1",
        # Special groups
        "H1",  # Historical
        "R0",  # Residual Latin-ASCII
        "Z0",  # Quarantine
    }

    # Expert Phase 3: Lexical signal ensemble configuration
    SIGNALS_DIR_ENV = "GMNAP_SIGNALS_DIR"
    SIGNALS_CACHE = None

    def __init__(self, config_dir: Path = Path("./config")):
        self.config_dir = config_dir
        self._regions: Dict[str, RegionSpec] = {}
        self._unicode_normalizer = UnicodeNormalizer()
        self._security_validator = SecurityValidator()  # Add security validation
        self._lang_detector = None
        self._lang_detector_loaded = False
        self._diaspora_config = {}
        self._doi_prefix_map = {}
        self._regions_loaded = False
        # Expert solution: Bounded cache to prevent memory growth
        self._detection_cache = SizedLRU(max_bytes=64 * 1024 * 1024)  # 64MB cache
        # Phase 2 ML models (stubs until trained)
        self._ml_models_loaded = False
        self._ft = None
        self._clf = None
        # Phase 3 Authority cache (SizedLRU with ~10MB limit)
        self._authority_cache = SizedLRU(max_bytes=10 * 1024 * 1024)
        self._initialize_core()

    def _load_signal_sets(self):
        """
        Expert Phase 3: Load JSONL signal files from GMNAP_SIGNALS_DIR (recursively).
        Caches in-memory for performance. Each signal has: id, region, subregion, kind,
        field, value, regex, weight, priority, gates (optional).
        """
        import glob
        import json
        import os

        if RegionManager.SIGNALS_CACHE is not None:
            return RegionManager.SIGNALS_CACHE
        base = os.environ.get(self.SIGNALS_DIR_ENV)
        out = []
        if base and os.path.isdir(base):
            for fp in glob.glob(os.path.join(base, "**", "*.jsonl"), recursive=True):
                with open(fp, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            out.append(json.loads(line))
                        except Exception:
                            continue
        RegionManager.SIGNALS_CACHE = out
        logger.info(
            f"Expert Phase 3: Loaded {len(out)} lexical signals from {base or 'no directory'}"
        )
        return out

    def _score_with_signals(self, entry):
        """
        Expert Phase 3: Score candidate regions using loaded lexical signals.
        Returns: (scores: dict[region_code->float], matched_signal_ids: list[str])
        """
        signals = self._load_signal_sets()
        full = (
            entry.get("CanonicalLatin") or entry.get("CanonicalNative") or ""
        ).lower()
        given = (entry.get("Given") or "").lower()
        surname = (entry.get("Surname") or "").lower()
        scores = {}
        matched = []
        for s in signals:
            # Skip country signatures (they use affiliation data, not name patterns)
            if "country" in s:
                continue
            # If Given/Surname not provided, try matching against full name for all fields
            if s["field"] == "full":
                field_text = full
            elif s["field"] == "given":
                field_text = given if given else full
            else:  # surname
                field_text = surname if surname else full
            if not field_text:
                continue
            val = s["value"]
            ok = False
            if s.get("regex"):
                import re

                try:
                    if re.search(val, field_text):
                        ok = True
                except re.error:
                    continue
            else:
                if s["kind"] == "prefix":
                    ok = field_text.startswith(val.strip())
                elif s["kind"] == "suffix":
                    ok = field_text.endswith(val)
                elif s["kind"] == "token":
                    # Token match requires word boundaries (not substring)
                    ok = f" {val} " in f" {field_text} " or field_text == val
                else:
                    ok = val in field_text
            if ok:
                r = s["region"]
                scores[r] = scores.get(r, 0.0) + float(s.get("weight", 1.0))
                matched.append(s["id"])
        return scores, matched

    def _detect_by_priority_signals(self, entry, fallback=None):
        """
        Expert Phase 3: Detect region using lexical signal ensemble.
        Returns detection result with region_code, confidence, method, and matched signals.
        """
        scores, matched = self._score_with_signals(entry)
        if not scores:
            return fallback
        best_region = max(scores.items(), key=lambda kv: kv[1])[0]
        conf = min(0.98, 0.50 + (scores[best_region] / 10.0))
        return {
            "region_code": best_region,
            "confidence": conf,
            "detection_method": "lex-signal-ensemble",
            "metadata": {"matched_signals": matched, "scores": scores},
        }

    def load_ml_models(
        self, fasttext_path: str | None = None, clf_path: str | None = None
    ):
        """Phase 2: Load ML models for ensemble detection."""
        if not FASTTEXT_AVAILABLE:
            logger.warning(
                "ML models not loaded: fasttext package not available (Docker minimal mode)"
            )
            self._ml_models_loaded = False
            return

        import pickle

        try:
            if fasttext_path:
                self._ft = fasttext.load_model(fasttext_path)
                logger.info(f"Loaded FastText model from {fasttext_path}")
            if clf_path:
                # Load the full model bundle (includes vectorizers)
                with open(clf_path, "rb") as f:
                    bundle = pickle.load(f)
                    self._clf = bundle["model"]
                    self._label_encoder = bundle["label_encoder"]
                    self._tfidf = bundle["tfidf"]
                    self._cat_vectorizer = bundle["cat_vectorizer"]
                logger.info(f"Loaded classifier bundle from {clf_path}")
            self._ml_models_loaded = True
        except Exception as e:
            logger.warning(f"Failed to load ML models: {e}")
            self._ml_models_loaded = False  # Hard fail-safe

    def _extract_ml_features(self, name: str):
        """Phase 2: Extract features matching training code."""
        import numpy as np

        name_lower = name.lower()
        tokens = name_lower.split()

        # Numeric features
        numeric_features = [
            len(name_lower),  # length
            len(tokens),  # token_count
            int("-" in name),  # has_hyphen
            int("'" in name),  # has_apostrophe
            np.mean([len(t) for t in tokens]) if tokens else 0,  # avg_token_len
            max([len(t) for t in tokens]) if tokens else 0,  # max_token_len
            (
                sum(1 for c in name_lower if c in "aeiou") / len(name_lower)
                if name_lower
                else 0
            ),  # vowel_ratio
            int(any(ord(c) > 127 for c in name)),  # has_diacritic
        ]

        # Categorical features (suffix/prefix patterns)
        suffix_2 = tokens[-1][-2:] if tokens and len(tokens[-1]) >= 2 else ""
        suffix_3 = tokens[-1][-3:] if tokens and len(tokens[-1]) >= 3 else ""
        suffix_4 = tokens[-1][-4:] if tokens and len(tokens[-1]) >= 4 else ""
        prefix_2 = tokens[0][:2] if tokens and len(tokens[0]) >= 2 else ""
        prefix_3 = tokens[0][:3] if tokens and len(tokens[0]) >= 3 else ""

        categorical = "_".join([suffix_2, suffix_3, suffix_4, prefix_2, prefix_3])

        return numeric_features, name_lower, categorical

    def _detect_by_ml_ensemble(
        self, entry: Dict[str, Any]
    ) -> Optional[RegionDetectionResult]:
        """Phase 2: ML ensemble detection using trained models."""
        if not self._ml_models_loaded:
            return None
        if not hasattr(self, "_clf") or self._clf is None:
            return None

        name = entry.get("CanonicalLatin") or entry.get("CanonicalNative") or ""
        if not name:
            return None

        try:
            import numpy as np

            # Extract features matching training
            numeric_feats, name_lower, categorical = self._extract_ml_features(name)

            # TF-IDF char n-grams
            tfidf_feats = self._tfidf.transform([name_lower]).toarray()

            # Categorical features
            cat_data = [{"cat": categorical}]
            cat_feats = self._cat_vectorizer.transform(cat_data)

            # Combine all features
            X = np.hstack(
                [np.array(numeric_feats).reshape(1, -1), tfidf_feats, cat_feats]
            )

            # Predict
            y_pred = self._clf.predict(X)[0]
            y_proba = self._clf.predict_proba(X)[0]

            region = self._label_encoder.inverse_transform([y_pred])[0]
            confidence = float(y_proba.max())

            # Optional: Combine with FastText if available
            ft_region = None
            if self._ft and hasattr(self._ft, "predict"):
                ft_pred = self._ft.predict(name.replace("-", " "), k=1)
                if ft_pred and len(ft_pred[0]) > 0:
                    ft_region = ft_pred[0][0].replace("__label__", "")

            # Only return if confidence >= 0.85 (expert's target)
            if confidence >= 0.85:
                return RegionDetectionResult(
                    region_code=region,
                    confidence=min(confidence, 0.95),
                    detection_method="ml-ensemble",
                    metadata={
                        "xgb_region": region,
                        "xgb_confidence": confidence,
                        "ft_region": ft_region,
                    },
                )

            return None

        except Exception as e:
            logger.debug(f"ML ensemble detection failed: {e}")
            return None

    async def _detect_by_external_authority(
        self, entry: Dict[str, Any]
    ) -> Optional[RegionDetectionResult]:
        """
        Phase 3: External authority detection (cache-only in OFFLINE mode).

        Per expert's spec: Only uses cache, never blocks on live API calls in Quick mode.
        Later: Add async fetchers (ORCID/Wikidata/DOI) with TTL caching.
        """
        import os

        # Only if OFFLINE=0 and cached hit exists; otherwise skip
        if os.getenv("OFFLINE", "1") == "1":
            return None
        gid = entry.get("GlobalID") or entry.get("ID")
        if not gid:
            return None
        hit = self._authority_cache.get(gid)
        if not hit:
            return None
        # hit = {"region": "E1", "conf": 0.95, "source": "orcid-country"}
        return RegionDetectionResult(
            region_code=hit["region"],
            confidence=hit["conf"],
            detection_method=f"auth-{hit['source']}",
            metadata={"authority_source": hit.get("source"), "cached": True},
        )

    def add_authority_cache_entry(
        self, global_id: str, region: str, confidence: float, source: str
    ):
        """
        Phase 3: Add an entry to the authority cache.

        Args:
            global_id: GlobalID or ID for the entry
            region: Region code (e.g., "E1", "A2")
            confidence: Confidence score (0.0-1.0, typically ≥0.90 for authorities)
            source: Source name (e.g., "orcid-country", "wikidata", "doi-affiliation")
        """
        if not global_id or not region:
            return

        cache_entry = {"region": region, "conf": confidence, "source": source}
        self._authority_cache.put(global_id, cache_entry)
        logger.debug(
            f"Added authority cache: {global_id} → {region} ({confidence:.2f}, {source})"
        )

    def load_authority_cache_from_file(self, filepath: str):
        """
        Phase 3: Load authority cache from JSON/JSONL file.

        Expected format (JSONL):
        {"id": "some-global-id", "region": "E1", "conf": 0.95, "source": "orcid-country"}

        Or JSON array:
        [{"id": "...", "region": "...", "conf": 0.95, "source": "..."}]
        """
        import json
        import os

        if not os.path.exists(filepath):
            logger.warning(f"Authority cache file not found: {filepath}")
            return 0

        count = 0
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                # Try JSONL first
                first_char = f.read(1)
                f.seek(0)

                if first_char == "[":
                    # JSON array
                    data = json.load(f)
                    for entry in data:
                        if "id" in entry and "region" in entry:
                            self.add_authority_cache_entry(
                                global_id=entry["id"],
                                region=entry["region"],
                                confidence=entry.get(
                                    "conf", entry.get("confidence", 0.95)
                                ),
                                source=entry.get("source", "file-import"),
                            )
                            count += 1
                else:
                    # JSONL
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            entry = json.loads(line)
                            if "id" in entry and "region" in entry:
                                self.add_authority_cache_entry(
                                    global_id=entry["id"],
                                    region=entry["region"],
                                    confidence=entry.get(
                                        "conf", entry.get("confidence", 0.95)
                                    ),
                                    source=entry.get("source", "file-import"),
                                )
                                count += 1
                        except json.JSONDecodeError:
                            continue

            logger.info(f"Loaded {count} authority cache entries from {filepath}")
            return count

        except Exception as e:
            logger.error(f"Failed to load authority cache from {filepath}: {e}")
            return 0

    def get_authority_cache_stats(self) -> Dict[str, Any]:
        """Phase 3: Get statistics about the authority cache."""
        return {
            "entries": (
                len(self._authority_cache._data)
                if hasattr(self._authority_cache, "_data")
                else 0
            ),
            "size_bytes": (
                self._authority_cache._size
                if hasattr(self._authority_cache, "_size")
                else 0
            ),
            "max_bytes": (
                self._authority_cache.max_bytes
                if hasattr(self._authority_cache, "max_bytes")
                else 0
            ),
        }

    @property
    def lang_detector(self):
        """Lazy-load the FastText language detector."""
        if not self._lang_detector_loaded:
            self._lang_detector_loaded = True
            self._lang_detector = get_fasttext_model(self.config_dir)
            if self._lang_detector:
                logger.info("FastText language detector loaded (lazy)")
            else:
                logger.warning("FastText language detector not available")
        return self._lang_detector

    def _initialize_core(self):
        """Initialize only core components (not regions)."""
        # FastText model will be loaded lazily when needed
        # self._lang_detector = get_fasttext_model(self.config_dir)

        # Load diaspora configuration
        self._load_diaspora_config()

        # Load DOI prefix mappings
        self._load_doi_prefix_map()

        # Initialize script to region mappings (only implemented regions)
        self._init_script_mappings()

        # Initialize surname pattern databases
        self._init_surname_patterns()

    def _load_diaspora_config(self):
        """Load diaspora overlay configuration."""
        diaspora_path = self.config_dir / "diaspora.yaml"
        if diaspora_path.exists():
            import yaml

            with open(diaspora_path) as f:
                self._diaspora_config = yaml.safe_load(f) or {}
            logger.info(
                f"Loaded diaspora config with {len(self._diaspora_config)} entries"
            )

    def _load_doi_prefix_map(self):
        """Load DOI prefix to country mappings."""
        # Common DOI prefixes and their associated countries
        self._doi_prefix_map = {
            "10.1007": "DE",  # Springer (Germany)
            "10.1016": "NL",  # Elsevier (Netherlands)
            "10.1038": "GB",  # Nature (UK)
            "10.1126": "US",  # Science (USA)
            "10.1002": "US",  # Wiley (USA)
            "10.1021": "US",  # ACS (USA)
            "10.1088": "GB",  # IOP (UK)
            "10.1103": "US",  # APS (USA)
            "10.1109": "US",  # IEEE (USA)
            "10.1145": "US",  # ACM (USA)
            "10.1137": "US",  # SIAM (USA)
            "10.1090": "US",  # AMS (USA)
            "10.1063": "US",  # AIP (USA)
            "10.1093": "GB",  # Oxford (UK)
            "10.1017": "GB",  # Cambridge (UK)
            "10.3390": "CH",  # MDPI (Switzerland)
            "10.1080": "GB",  # Taylor & Francis (UK)
            "10.1111": "GB",  # Blackwell (UK)
            "10.1155": "US",  # Hindawi (USA/Egypt)
            "10.1371": "US",  # PLOS (USA)
            "10.4171": "CH",  # EMS (Switzerland)
        }

    def _init_script_mappings(self):
        """Initialize Unicode script to region mappings (all V7 regions)."""
        # Map to all V7 regions that are actually implemented
        self._script_to_regions = {
            "Latin": [
                r
                for r in [
                    # Western families first (still candidates)
                    "A1",
                    "A2",
                    "A3",
                    "A4",
                    "A5",
                    # Slavic & Greek (romanized forms common)
                    "B1",
                    "B2",
                    "B3",  # East Slavic, South Slavic, Greek (romanized)
                    # Middle East & Caucasus (all can be romanized)
                    "C1",
                    "C2",
                    "C3",
                    "C4",
                    "C5",
                    "C6",
                    "C7",
                    "C8",
                    "C9",
                    # South Asia (romanized extensively)
                    "D1",
                    "D2",
                    "D3",
                    "D4",
                    "D5",
                    # East/Southeast Asia (romanized forms)
                    "E1",  # Sinophone Mainland (Pinyin)
                    "E2",  # Traditional Chinese (Wade-Giles/Cantonese)
                    "E3",  # Japan (Hepburn/Kunrei romanization)
                    "E4",  # Korea (RR/MR romanization)
                    "E5",  # Vietnam (Quốc ngữ Latin script)
                    "E6",  # Mainland SEA (Thai/Lao/Khmer/Myanmar romanized)
                    "E7",  # Maritime SEA (Indonesian/Malay/Filipino Latin)
                    # Sub-Saharan Africa (mostly Latin script)
                    "F1",
                    "F2",
                    "F3",
                    "F4",
                    # Latin America
                    "G1",
                    # Special regions
                    "H1",  # Historical (Latin/romanized classical names)
                    "R0",  # Residual Latin ASCII
                ]
                if r in self.IMPLEMENTED_REGIONS
            ],
            "Cyrillic": [
                r for r in ["B1", "B2", "C1", "C9"] if r in self.IMPLEMENTED_REGIONS
            ],
            "Greek": [r for r in ["B3"] if r in self.IMPLEMENTED_REGIONS],
            "Arabic": [
                r
                for r in ["C1", "C2", "C3", "C4", "C5"]
                if r in self.IMPLEMENTED_REGIONS
            ],
            "Hebrew": [r for r in ["C6"] if r in self.IMPLEMENTED_REGIONS],
            "Devanagari": [r for r in ["D1", "D2"] if r in self.IMPLEMENTED_REGIONS],
            "Bengali": [r for r in ["D3"] if r in self.IMPLEMENTED_REGIONS],
            "Tamil": [r for r in ["D2"] if r in self.IMPLEMENTED_REGIONS],
            "Telugu": [r for r in ["D2"] if r in self.IMPLEMENTED_REGIONS],
            "Sinhala": [r for r in ["D5"] if r in self.IMPLEMENTED_REGIONS],
            "Thai": [r for r in ["E6"] if r in self.IMPLEMENTED_REGIONS],
            "Myanmar": [r for r in ["E6"] if r in self.IMPLEMENTED_REGIONS],
            "Georgian": [r for r in ["C8"] if r in self.IMPLEMENTED_REGIONS],
            "Armenian": [r for r in ["C7"] if r in self.IMPLEMENTED_REGIONS],
            "CJK": [r for r in ["E1", "E2", "E3"] if r in self.IMPLEMENTED_REGIONS],
            "Hangul": [r for r in ["E4"] if r in self.IMPLEMENTED_REGIONS],
            "Ethiopic": [r for r in ["F3"] if r in self.IMPLEMENTED_REGIONS],
            "Vietnamese": [r for r in ["E5"] if r in self.IMPLEMENTED_REGIONS],
            "Khmer": [r for r in ["E6"] if r in self.IMPLEMENTED_REGIONS],
            "Lao": [r for r in ["E6"] if r in self.IMPLEMENTED_REGIONS],
            "Malay": [r for r in ["E7"] if r in self.IMPLEMENTED_REGIONS],
        }

    def _ensure_regions_loaded(self):
        """Lazy load regions only when needed."""
        if not self._regions_loaded:
            self._load_regions()
            self._regions_loaded = True

    def register_region(self, region: RegionSpec) -> None:
        """Register a region specification."""
        # Only register if it's in the implemented list
        if region.code in self.IMPLEMENTED_REGIONS:
            self._regions[region.code] = region
            logger.info(
                f"Registered region {region.code}: {REGION_CODES.get(region.code)}"
            )
        else:
            logger.debug(f"Skipping unimplemented region {region.code}")

    def get_region(self, code: str) -> Optional[RegionSpec]:
        """Get region specification by code."""
        self._ensure_regions_loaded()
        return self._regions.get(code)

    def detect_region(self, entry: Dict[str, Any]) -> RegionDetectionResult:
        """
        Detect region for an entry using multi-stage detection.

        Args:
            entry: Dictionary containing entry data
        """
        # SECURITY: Validate and sanitize entry before processing
        try:
            sanitized_entry = self._security_validator.validate_entry(entry)
        except SecurityError as e:
            # Return safe error result without exposing attack details
            logger.warning(f"Security validation failed: {e}")
            return RegionDetectionResult(
                region_code="XX",  # Unknown/error region
                confidence=0.0,
                detection_method="security_blocked",
                metadata={"error": "Invalid input detected"},
            )

        # Ensure regions are loaded
        self._ensure_regions_loaded()

        # Create cache key from sanitized entry data — include CountryCodes
        # to avoid collisions when the same name appears with different CCs
        # (e.g. "Lee, Bruce" with CC=US vs CC=KR must not share a cache slot).
        cc = ",".join(sanitized_entry.get("CountryCodes", []))
        cache_key = (
            (
                sanitized_entry.get("CanonicalLatin", "")
                or sanitized_entry.get("CanonicalNative", "")
            )
            + "|"
            + cc
        )

        # Check cache
        cached_result = self._detection_cache.get(cache_key)
        if cached_result is not None:
            return cached_result

        # Detect region using sanitized entry (sync wrapper for async method)
        import asyncio

        try:
            # Try to get running loop
            loop = asyncio.get_running_loop()
            # If we're already in async context, can't use run_until_complete
            # Create a task instead
            loop.create_task(self._detect_region_uncached_async(sanitized_entry))
            # For sync calls from async context, we need to handle differently
            # For now, fall back to sync-only detection
            result = self._detect_region_uncached_sync(sanitized_entry)
        except RuntimeError:
            # No running loop - safe to use asyncio.run()
            result = asyncio.run(self._detect_region_uncached_async(sanitized_entry))

        # Cache result
        if cache_key:
            self._detection_cache.put(cache_key, result)

        return result

    def _detect_region_uncached_sync(
        self, entry: Dict[str, Any]
    ) -> RegionDetectionResult:
        """
        Synchronous version of region detection.
        Used when called from async context to avoid nested event loops.

        Expert-specified cascade (Phase 1-3):
        0. Authority (Phase 3) - ≥0.90 → early return (cache-only, no async needed)
        1. ML Ensemble (Phase 2) - ≥0.85 → early return
        2. Surname Pattern Matching - >0.95 → early return
        3. Script Analysis (Priority Rules - Phase 1) - ≥0.60 → early return
        """
        # HIGHEST PRIORITY: Country code → region mapping
        country_codes = entry.get("CountryCodes", [])
        if country_codes:
            from src.regions.base import get_region_for_territory

            region = get_region_for_territory(country_codes[0])
            if region in self.IMPLEMENTED_REGIONS:
                return RegionDetectionResult(
                    region_code=region,
                    confidence=0.85,
                    detection_method="country-code",
                    metadata={"country": country_codes[0]},
                )

        # Phase 3: Authority detection (cache-only, synchronous)
        import os

        if os.getenv("OFFLINE", "1") == "0":
            gid = entry.get("GlobalID") or entry.get("ID")
            if gid:
                hit = self._authority_cache.get(gid)
                if hit:
                    result = RegionDetectionResult(
                        region_code=hit["region"],
                        confidence=hit["conf"],
                        detection_method=f"auth-{hit['source']}",
                        metadata={
                            "authority_source": hit.get("source"),
                            "cached": True,
                        },
                    )
                    if result.confidence >= 0.90:
                        return result

        # Phase 2: ML ensemble (returns None if models not loaded)
        result = self._detect_by_ml_ensemble(entry)
        if result and result.confidence >= 0.85:
            return result

        # PHASE 3 FIX 1: Hybrid name detection (CJK surname + Latin given)
        result = self._detect_hybrid_name(entry)
        if result and result.confidence >= 0.95:
            return result

        # Phase 1: Surname pattern matching (only if very confident)
        result = self._detect_by_surname(entry)
        if result and result.confidence > 0.95:
            return result

        # Phase 1: Script Analysis with priority rules
        result = self._detect_by_script(entry)
        if result and result.confidence >= 0.60:
            # PHASE 3 FIX 2: Apply affiliation tie-breaking
            result = self._apply_affiliation_tiebreak(entry, result)
            return result

        # Phase 1: ICU processing with priority rules
        result = self._detect_by_icu(entry)
        if result and result.confidence >= 0.60:
            # PHASE 3 FIX 2: Apply affiliation tie-breaking
            result = self._apply_affiliation_tiebreak(entry, result)
            return result

        # FastText language detection
        if self.lang_detector:
            result = self._detect_by_language(entry)
            if result and result.confidence >= 0.7:
                return result

        # Affiliation hints
        result = self._detect_by_affiliation(entry)
        if result:
            return result

        # DOI prefix
        result = self._detect_by_doi(entry)
        if result:
            return result

        # Diaspora overlay
        result = self._detect_by_diaspora(entry)
        if result:
            return result

        # Fallback based on country code
        country_codes = entry.get("CountryCodes", [])
        if country_codes:
            region = get_region_for_territory(country_codes[0])
            if region in self.IMPLEMENTED_REGIONS:
                return RegionDetectionResult(
                    region_code=region,
                    confidence=0.3,
                    detection_method="country-fallback",
                    metadata={},
                )

        # Last resort
        return RegionDetectionResult(
            region_code="R0", confidence=0.1, detection_method="fallback", metadata={}
        )

    async def _detect_region_uncached_async(
        self, entry: Dict[str, Any]
    ) -> RegionDetectionResult:
        """
        Detect region for an entry using V7-compliant multi-stage detection.

        Expert-specified cascade (Phase 1-3):
        0. Authority (Phase 3) - ≥0.90 → early return
        1. ML Ensemble (Phase 2) - ≥0.85 → early return
        2. Surname Pattern Matching - >0.95 → early return
        3. Script Analysis (Priority Rules - Phase 1) - ≥0.60 → early return
        4. ICU Processing (Priority Rules - Phase 1) - ≥0.60 → early return
        5. FastText Language Detection
        6. Affiliation Hints
        7. DOI Prefix / Diaspora Overlay
        8. Fallback (0.40-0.60)
        """
        # HIGHEST PRIORITY: Country code → region mapping
        country_codes = entry.get("CountryCodes", [])
        if country_codes:
            from src.regions.base import get_region_for_territory

            region = get_region_for_territory(country_codes[0])
            if region in self.IMPLEMENTED_REGIONS:
                return RegionDetectionResult(
                    region_code=region,
                    confidence=0.85,
                    detection_method="country-code",
                    metadata={"country": country_codes[0]},
                )

        # Phase 3: Authority detection (cached only in OFFLINE mode)
        result = await self._detect_by_external_authority(entry)
        if result and result.confidence >= 0.90:
            return result

        # Phase 2: ML ensemble (returns None if models not loaded)
        result = self._detect_by_ml_ensemble(entry)
        if result and result.confidence >= 0.85:
            return result

        # PHASE 3 FIX 1: Hybrid name detection (CJK surname + Latin given)
        # Expert: "CJK surname trumps Anglo given name"
        # This must happen BEFORE general surname matching to avoid false A1 classification
        result = self._detect_hybrid_name(entry)
        if result and result.confidence >= 0.95:
            return result

        # Phase 1: Surname pattern matching (only if very confident)
        # Threshold > 0.95 so priority rules in script/ICU can handle most cases
        result = self._detect_by_surname(entry)
        if result and result.confidence > 0.95:
            return result

        # Phase 1: Script Analysis with priority rules
        result = self._detect_by_script(entry)
        if result and result.confidence >= 0.60:
            # PHASE 3 FIX 2: Apply affiliation tie-breaking for ambiguous families
            # Expert: "Use affiliation ONLY for tie-breaking within families (A2/G1, E1/E2, C3/C4/C5)"
            result = self._apply_affiliation_tiebreak(entry, result)
            return result

        # Phase 1: ICU processing with priority rules
        result = self._detect_by_icu(entry)
        if result and result.confidence >= 0.60:
            # PHASE 3 FIX 2: Apply affiliation tie-breaking for ambiguous families
            result = self._apply_affiliation_tiebreak(entry, result)
            return result

        # FastText language detection
        if self.lang_detector:
            result = self._detect_by_language(entry)
            if result and result.confidence >= 0.7:
                return result

        # Affiliation hints
        result = self._detect_by_affiliation(entry)
        if result:
            return result

        # DOI prefix
        result = self._detect_by_doi(entry)
        if result:
            return result

        # Diaspora overlay
        result = self._detect_by_diaspora(entry)
        if result:
            return result

        # Fallback based on country code
        country_codes = entry.get("CountryCodes", [])
        if country_codes:
            region = get_region_for_territory(country_codes[0])
            # Only return if it's an implemented region
            if region in self.IMPLEMENTED_REGIONS:
                return RegionDetectionResult(
                    region_code=region,
                    confidence=0.3,
                    detection_method="country-fallback",
                    metadata={"country": country_codes[0]},
                )

        # Default fallback - but only if A1 is implemented
        if "A1" in self.IMPLEMENTED_REGIONS:
            return RegionDetectionResult(
                region_code="A1",
                confidence=0.1,
                detection_method="default-fallback",
                metadata={},
            )
        else:
            # No implemented regions available - should not happen
            return RegionDetectionResult(
                region_code="Z0",
                confidence=0.0,
                detection_method="no-regions",
                metadata={},
            )

    def _detect_by_script(
        self, entry: Dict[str, Any]
    ) -> Optional[RegionDetectionResult]:
        """Detect region based on Unicode script analysis with priority rules + fallback."""
        name = entry.get("CanonicalLatin") or entry.get("CanonicalNative") or ""
        if not name:
            return None
        scripts = self._analyze_scripts(name)
        total = sum(scripts.values()) or 1
        dominant, dom_count = max(scripts.items(), key=lambda kv: kv[1])
        if dom_count / total < 0.5:
            return None
        possible = self._script_to_regions.get(dominant, [])

        # EXPERT PHASE 3: Try lexical signal ensemble first (replaces old priority rules)
        signal_result = self._detect_by_priority_signals(entry)
        if signal_result and signal_result.get("region_code") in possible:
            # Signal matched one of the script-compatible regions
            dom_ratio = min(1.0, dom_count / total)
            signal_conf = signal_result.get("confidence", 0.0)
            # Blend script dominance with signal confidence
            final_conf = min(0.95, 0.3 * dom_ratio + 0.7 * signal_conf)
            final_conf = _nudge_by_doi_affiliation(
                entry, signal_result["region_code"], final_conf
            )
            return RegionDetectionResult(
                region_code=signal_result["region_code"],
                confidence=final_conf,
                detection_method="script-signal-ensemble",
                metadata={
                    "script": dominant,
                    "script_ratio": dom_ratio,
                    "signal_confidence": signal_conf,
                    **signal_result.get("metadata", {}),
                },
            )

        # Fallback to OLD priority rules if signals don't match script-compatible regions
        region, conf, dbg = _score_priority_rules(name, possible)
        if region and conf >= 0.60:
            dom_ratio = min(1.0, dom_count / total)
            final_conf = min(0.90, 0.5 * dom_ratio + 0.5 * conf)
            final_conf = _nudge_by_doi_affiliation(entry, region, final_conf)
            return RegionDetectionResult(
                region_code=region,
                confidence=final_conf,
                detection_method="script-priority",
                metadata={"script": dominant, "script_ratio": dom_ratio, **dbg},
            )

        # Fallback to original selector for names not in priority lexicons
        best_region = self._select_best_region_from_script(entry, possible)
        if best_region:
            confidence = 0.7 if dominant == "Latin" else dom_count / total
            final_conf = _nudge_by_doi_affiliation(entry, best_region, confidence)
            return RegionDetectionResult(
                region_code=best_region,
                confidence=final_conf,
                detection_method="script",
                metadata={"script": dominant, "script_ratio": dom_count / total},
            )
        return None

    def _detect_by_icu(self, entry: Dict[str, Any]) -> Optional[RegionDetectionResult]:
        """V7 Stage 2: ICU processing - Unicode normalization with priority rules."""
        name = entry.get("CanonicalLatin") or entry.get("CanonicalNative") or ""
        if not name:
            return None
        icu_name = self._unicode_normalizer.normalize(name)  # ICU normalization
        scripts = self._analyze_scripts(icu_name)
        total = sum(scripts.values()) or 1
        dominant, dom_count = max(scripts.items(), key=lambda kv: kv[1])
        possible = self._script_to_regions.get(dominant, [])
        region, conf, dbg = _score_priority_rules(icu_name, possible)
        if region:
            final_conf = min(
                0.90, 0.4 * (dom_count / total) + 0.6 * conf
            )  # ICU shouldn't auto-win
            final_conf = _nudge_by_doi_affiliation(entry, region, final_conf)
            return RegionDetectionResult(
                region_code=region,
                confidence=final_conf,
                detection_method="icu-priority",
                metadata={"script": dominant, "icu": True, **dbg},
            )
        return None

    def _select_best_region_from_script(
        self, entry: Dict[str, Any], possible_regions: List[str]
    ) -> Optional[str]:
        """Select best region from script matches using surname patterns and country codes."""
        # Get country code
        country_codes = entry.get("CountryCodes", [])
        if country_codes:
            country = country_codes[0]
            # Check if country directly maps to one of the possible regions
            expected_region = get_region_for_territory(country)
            if (
                expected_region in possible_regions
                and expected_region in self.IMPLEMENTED_REGIONS
            ):
                return expected_region

        # Use surname pattern detection for Latin script regions
        name = entry.get("CanonicalLatin", "") or entry.get("CanonicalNative", "")
        if name and "Latin" in [
            script
            for script, regions in self._script_to_regions.items()
            if any(r in possible_regions for r in regions)
        ]:
            surname_region = self._detect_by_surname_patterns(name, possible_regions)
            if surname_region and surname_region in self.IMPLEMENTED_REGIONS:
                return surname_region

            # Additional pattern matching for romanized names (fallback if surname patterns didn't match)
            name_lower = name.lower()

            # Chinese romanized surnames (E1)
            chinese_surnames = [
                "li ",
                "wang ",
                "zhang ",
                "liu ",
                "chen ",
                "yang ",
                "huang ",
                "zhao ",
                "wu ",
                "zhou ",
                "xu ",
                "sun ",
                "lu ",
                "shen",
            ]
            if any(pattern in name_lower for pattern in chinese_surnames):
                if "E1" in possible_regions and "E1" in self.IMPLEMENTED_REGIONS:
                    return "E1"

            # Indian surnames (D1/D3)
            indian_surnames = [
                "singh",
                "kumar",
                "sharma",
                "gupta",
                "biswas",
                "banerjee",
                "chatterjee",
                "das",
                "bal",
            ]
            if any(pattern in name_lower for pattern in indian_surnames):
                if "D3" in possible_regions and "D3" in self.IMPLEMENTED_REGIONS:
                    return "D3"
                if "D1" in possible_regions and "D1" in self.IMPLEMENTED_REGIONS:
                    return "D1"

            # Korean romanized surnames (E4)
            korean_surnames = [
                "kim ",
                "lee ",
                "park ",
                "choi ",
                "jung ",
                "jeon ",
                "kang ",
            ]
            if any(pattern in name_lower for pattern in korean_surnames):
                if "E4" in possible_regions and "E4" in self.IMPLEMENTED_REGIONS:
                    return "E4"

            # Persian surnames (C2)
            persian_patterns = ["zadeh", "pour", "feyzbakhsh", "khani"]
            if any(pattern in name_lower for pattern in persian_patterns):
                if "C2" in possible_regions and "C2" in self.IMPLEMENTED_REGIONS:
                    return "C2"

        # Apply heuristics based on script type
        canonical = entry.get("CanonicalNative", "") or entry.get("CanonicalLatin", "")

        # CJK script heuristics (only if name contains CJK characters)
        scripts = self._analyze_scripts(canonical)
        has_cjk = scripts.get("CJK", 0) > 0

        if has_cjk and any(region in ["E1", "E2", "E3"] for region in possible_regions):
            # Improved Japanese detection using more specific patterns
            # Japanese-specific surname combinations and patterns
            japanese_surname_patterns = [
                "田中",
                "山田",
                "佐藤",
                "鈴木",
                "高橋",
                "田口",
                "川口",
                "木村",
                "林田",
            ]
            chinese_indicators = [
                "王",
                "李",
                "张",
                "刘",
                "陈",
                "杨",
                "黄",
                "赵",
                "吴",
                "周",
                "小明",
                "小红",
                "小华",
            ]

            # Check for explicit Chinese patterns first
            if any(indicator in canonical for indicator in chinese_indicators):
                if "E1" in possible_regions and "E1" in self.IMPLEMENTED_REGIONS:
                    return "E1"

            # Check for Japanese surname patterns
            if any(pattern in canonical for pattern in japanese_surname_patterns):
                if "E3" in possible_regions and "E3" in self.IMPLEMENTED_REGIONS:
                    return "E3"

            # Check for Japanese-specific combinations (surname + taro/ko/etc)
            if any(ending in canonical for ending in ["太郎", "花子", "一郎", "次郎"]):
                if "E3" in possible_regions and "E3" in self.IMPLEMENTED_REGIONS:
                    return "E3"

            # Default to Chinese for most CJK content
            if "E1" in possible_regions and "E1" in self.IMPLEMENTED_REGIONS:
                return "E1"

        # Arabic script heuristics - prioritize C3 (Arabic) over C1 (Turkic)
        if any(region in ["C1", "C2", "C3", "C4", "C5"] for region in possible_regions):
            if "C3" in possible_regions and "C3" in self.IMPLEMENTED_REGIONS:
                return "C3"

        # Fallback to first implemented region
        for region in possible_regions:
            if region in self.IMPLEMENTED_REGIONS:
                return region

        return None

    def _detect_by_surname(
        self, entry: Dict[str, Any]
    ) -> Optional[RegionDetectionResult]:
        """Detect region using direct surname pattern matching."""
        name = entry.get("CanonicalLatin", "")
        if not name:
            return None

        # Extract surname from "Family, Given" format
        if "," in name:
            family_name = name.split(",")[0].strip().lower()
        else:
            # For names without comma, check both first and last parts
            # as different cultures place surnames differently
            parts = name.strip().split()
            if len(parts) < 2:
                return None

            # Check both possibilities: "Family Given" (Korean/Chinese/Japanese) and "Given Family" (Western)
            candidates = [
                parts[0].lower(),  # First part (Korean/CJK style)
                parts[-1].lower(),  # Last part (Western style)
            ]

            # Find best match from both candidates
            best_match = None
            best_score = 0
            best_surname = None

            # Track ambiguous matches
            matches = []

            for candidate in candidates:
                # Clean surname for matching
                cleaned_candidate = self._clean_surname_for_matching(candidate)

                for region_code, surnames in self.surname_patterns.items():
                    # Only check implemented regions
                    if region_code not in self.IMPLEMENTED_REGIONS:
                        continue

                    score = 0

                    # Direct match
                    if cleaned_candidate in surnames:
                        score = 10
                        # For ambiguous surnames like "Lee", check given name patterns
                        if (
                            cleaned_candidate in ["lee", "li", "kim"]
                            and len(parts) >= 2
                        ):
                            # Check for Western and Korean given name patterns
                            given_parts = (
                                parts[1:]
                                if candidate == parts[0].lower()
                                else parts[:-1]
                            )
                            given_str = " ".join(given_parts).lower()

                            # Check if any given name part is clearly Western
                            has_western_given = any(
                                self._is_western_given_name(part)
                                for part in given_parts
                            )

                            # Common Korean given name patterns and surnames used as given names
                            korean_patterns = [
                                "-",
                                "jong",
                                "sung",
                                "jin",
                                "min",
                                "hyun",
                                "jung",
                                "bak",
                                "hoon",
                                "woo",
                                "jae",
                                "young",
                                "seok",
                                "han",
                                "lee",
                                "kim",
                                "park",
                                "choi",
                                "cho",
                                "kang",
                                "yoon",
                                "jang",
                            ]
                            has_korean_pattern = any(
                                p in given_str for p in korean_patterns
                            )

                            if has_western_given and region_code.startswith("A"):
                                score = 15  # Strong boost for Western given names with Western regions
                            elif has_korean_pattern and region_code == "E4":
                                score = 12  # Boost Korean match
                            elif (
                                not has_korean_pattern
                                and not has_western_given
                                and region_code != "E4"
                            ):
                                score = 11  # Slight boost for non-Korean
                            elif has_western_given and region_code == "E4":
                                score = 5  # Reduce Korean score for Western given names
                    else:
                        # Partial match scoring - only for surnames of reasonable length
                        for surname in surnames:
                            # Skip very short surnames for partial matching to avoid false positives
                            if len(surname) < 3 or len(cleaned_candidate) < 3:
                                continue

                            # Prefix matching (more reliable)
                            if cleaned_candidate.startswith(
                                surname
                            ) or surname.startswith(cleaned_candidate):
                                score = max(score, 7)
                            # Substring matching (less reliable, require longer match)
                            elif len(surname) >= 4 and len(cleaned_candidate) >= 4:
                                if (
                                    surname in cleaned_candidate
                                    or cleaned_candidate in surname
                                ):
                                    score = max(score, 5)

                    if score >= 10:
                        matches.append((region_code, score, cleaned_candidate))

                    if score > best_score:
                        best_score = score
                        best_match = region_code
                        best_surname = cleaned_candidate

            if best_match and best_score >= 5:
                confidence = 0.95 if best_score >= 10 else 0.85
                return RegionDetectionResult(
                    region_code=best_match,
                    confidence=confidence,
                    detection_method="surname",
                    metadata={"surname": best_surname, "score": best_score},
                )

            return None

        # For comma-separated names, process normally
        # Clean surname for matching
        family_name = self._clean_surname_for_matching(family_name)

        # Score each region based on surname matches
        region_scores = {}

        for region_code, surnames in self.surname_patterns.items():
            # Only check implemented regions
            if region_code not in self.IMPLEMENTED_REGIONS:
                continue

            score = 0

            # Direct match
            if family_name in surnames:
                score = 10
                # For ambiguous surnames, check given name for disambiguation
                if family_name in ["lee", "li", "kim"] and "," in name:
                    given_parts = name.split(",")[1].strip().lower()
                    # Common Korean given name patterns
                    korean_patterns = [
                        "-",
                        "jong",
                        "sung",
                        "jin",
                        "min",
                        "hyun",
                        "jung",
                        "myung",
                        "bak",
                        "hoon",
                        "woo",
                        "jae",
                        "young",
                        "seok",
                        "han",
                    ]
                    has_korean_pattern = any(p in given_parts for p in korean_patterns)

                    if has_korean_pattern and region_code == "E4":
                        score = 12  # Boost Korean match
                    elif not has_korean_pattern and region_code != "E4":
                        score = 11  # Slight boost for non-Korean
            else:
                # Partial match scoring - only for surnames of reasonable length
                for surname in surnames:
                    # Skip very short surnames for partial matching to avoid false positives
                    if len(surname) < 3 or len(family_name) < 3:
                        continue

                    # Prefix matching (more reliable)
                    if family_name.startswith(surname) or surname.startswith(
                        family_name
                    ):
                        score = max(score, 7)
                    # Substring matching (less reliable, require longer match)
                    elif len(surname) >= 4 and len(family_name) >= 4:
                        if surname in family_name or family_name in surname:
                            score = max(score, 5)

            if score > 0:
                region_scores[region_code] = score

        if region_scores:
            best_score = max(region_scores.values())
            if best_score >= 5:
                # Get all regions with the best score
                best_matches = [r for r, s in region_scores.items() if s == best_score]

                if len(best_matches) == 1:
                    best_match = best_matches[0]
                else:
                    # Prefer E4 for ambiguous Asian surnames
                    if "E4" in best_matches and family_name in [
                        "lee",
                        "li",
                        "kim",
                        "park",
                        "choi",
                    ]:
                        best_match = "E4"
                    else:
                        best_match = best_matches[0]
            confidence = 0.95 if best_score >= 10 else 0.85
            return RegionDetectionResult(
                region_code=best_match,
                confidence=confidence,
                detection_method="surname",
                metadata={"surname": family_name, "score": best_score},
            )

        return None

    def _detect_by_language(
        self, entry: Dict[str, Any]
    ) -> Optional[RegionDetectionResult]:
        """Detect region based on language identification."""
        if not self.lang_detector:
            return None

        text = entry.get("CanonicalLatin", "") or entry.get("CanonicalNative", "")
        if not text or len(text) < 10:  # Need reasonable text length
            return None

        try:
            # FastText returns ((label,), (confidence,))
            predictions = self.lang_detector.predict(text, k=3)

            # Map language codes to regions (only implemented ones)
            lang_to_region = {
                "en": "A1",
                "es": "G1",
                "pt": "G1",
                "fr": "A2",
                "de": "A2",
                "it": "A2",
                "nl": "A2",
                "ru": "B1",
                "uk": "B1",
                "pl": "B2",
                "cs": "B2",
                "sk": "B2",
                "hr": "B2",
                "sr": "B2",
                "sl": "B2",
                "ar": "C3",
                "fa": "C2",
                "tr": "C1",
                "he": "C6",
                "hi": "D1",
                "ur": "D4",
                "bn": "D3",
                "ta": "D2",
                "te": "D2",
                "si": "D5",
                "zh": "E1",
                "ja": "E3",
                "ko": "E4",
                "vi": "E5",
                "th": "E6",
                "id": "E7",
                "ms": "E7",
                "tl": "E7",
                "sw": "F1",
                "am": "F3",
            }

            for (lang_label,), (conf,) in zip(predictions[0], predictions[1]):
                lang_code = lang_label.replace("__label__", "")
                region = lang_to_region.get(lang_code)
                if region and region in self.IMPLEMENTED_REGIONS and conf > 0.5:
                    return RegionDetectionResult(
                        region_code=region,
                        confidence=min(conf, 0.9),  # Cap confidence
                        detection_method="language",
                        metadata={"language": lang_code, "lang_confidence": conf},
                    )
        except Exception as e:
            logger.debug(f"Language detection failed: {e}")

        return None

    def _detect_by_affiliation(
        self, entry: Dict[str, Any]
    ) -> Optional[RegionDetectionResult]:
        """Detect region based on affiliation information."""
        affiliations = entry.get("Affiliations", [])
        if not affiliations:
            return None

        # Extract country from affiliation
        # This is a simplified version - real implementation would be more sophisticated
        for affiliation in affiliations:
            if isinstance(affiliation, dict):
                country = affiliation.get("country")
                if country:
                    region = get_region_for_territory(country)
                    if region and region in self.IMPLEMENTED_REGIONS:
                        return RegionDetectionResult(
                            region_code=region,
                            confidence=0.8,
                            detection_method="affiliation",
                            metadata={
                                "country": country,
                                "affiliation": affiliation.get("name"),
                            },
                        )

        return None

    def _detect_by_doi(self, entry: Dict[str, Any]) -> Optional[RegionDetectionResult]:
        """Detect region based on DOI prefix."""
        dois = entry.get("DOIs", [])
        if not dois:
            return None

        for doi in dois:
            # Extract prefix (e.g., "10.1007" from "10.1007/s00220-021-04123-0")
            if "/" in doi:
                prefix = doi.split("/")[0]
                country = self._doi_prefix_map.get(prefix)
                if country:
                    region = get_region_for_territory(country)
                    if region and region in self.IMPLEMENTED_REGIONS:
                        return RegionDetectionResult(
                            region_code=region,
                            confidence=0.6,
                            detection_method="doi",
                            metadata={"doi_prefix": prefix, "country": country},
                        )

        return None

    def _detect_by_diaspora(
        self, entry: Dict[str, Any]
    ) -> Optional[RegionDetectionResult]:
        """Detect region based on diaspora patterns."""
        # Simplified diaspora detection
        name = entry.get("CanonicalLatin", "")
        countries = entry.get("CountryCodes", [])

        if not name or not countries:
            return None

        # Example: Chinese name in USA -> Still E1
        # This would use the diaspora config in real implementation

        return None

    def _detect_hybrid_name(
        self, entry: Dict[str, Any]
    ) -> Optional[RegionDetectionResult]:
        """
        Detect hybrid names (Latin given + CJK surname).

        Expert's guidance: "CJK surname trumps Anglo given name"
        Examples:
        - Robert Chen → E1 (Chinese surname primary)
        - Michael Kim → E4 (Korean surname primary)
        - Jennifer Lee → E4 (Korean surname primary)

        Works on both:
        1. Mixed script names (Latin + Chinese characters/Hangul)
        2. Pure Latin romanizations (Robert Chen, etc.)

        Returns early with high confidence (0.95) if CJK surname detected.
        """
        name = entry.get("CanonicalLatin") or entry.get("CanonicalNative") or ""
        if not name:
            return None

        # Extract tokens
        tokens = name.split()
        if len(tokens) < 2:
            return None

        # Common Anglo given names (to detect hybrid pattern)
        # Only trigger if we have Anglo given + CJK surname
        anglo_given_names = {
            "robert",
            "michael",
            "david",
            "jennifer",
            "daniel",
            "daniel",
            "john",
            "james",
            "william",
            "richard",
            "joseph",
            "thomas",
            "charles",
            "christopher",
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
            "jason",
            "jeffrey",
            "ryan",
            "jacob",
            "gary",
            "nicholas",
            "eric",
            "jonathan",
            "stephen",
            "larry",
            "justin",
            "scott",
            "brandon",
            "benjamin",
            "samuel",
            "raymond",
            "gregory",
            "mary",
            "patricia",
            "linda",
            "barbara",
            "elizabeth",
            "susan",
            "jessica",
            "sarah",
            "karen",
            "nancy",
            "lisa",
            "betty",
            "margaret",
            "sandra",
            "ashley",
            "dorothy",
            "kimberly",
            "emily",
            "donna",
            "michelle",
            "carol",
            "amanda",
            "melissa",
            "deborah",
            "stephanie",
            "rebecca",
            "sharon",
            "laura",
            "cynthia",
            "kathleen",
            "amy",
            "anna",
            "angela",
            "martha",
            "ruth",
            "christine",
            "diane",
        }

        # Check if first token is an Anglo given name
        first_token = tokens[0].lower()
        has_anglo_given = first_token in anglo_given_names

        # Common Chinese surnames (1-2 char, Latin romanization)
        chinese_surnames = {
            "wang",
            "li",
            "zhang",
            "liu",
            "chen",
            "yang",
            "zhao",
            "huang",
            "zhou",
            "wu",
            "xu",
            "sun",
            "ma",
            "zhu",
            "hu",
            "guo",
            "lin",
            "he",
            "gao",
            "luo",
            "zheng",
            "liang",
            "xie",
            "song",
            "tang",
            "han",
            "feng",
            "yu",
            "dong",
            "xiao",
            "cheng",
            "cao",
            "yuan",
            "deng",
            "xu",
            "fu",
            "shen",
            "peng",
            "lu",
            "su",
            "lu",
            "jiang",
            "cai",
            "jia",
            "ding",
            "wei",
            "xue",
            "ye",
            "yan",
            "pan",
            "du",
            "dai",
            "xia",
            "zhong",
            "wang",
            "tian",
            "ren",
            "jiang",
            "fan",
            "shi",
            "yao",
            "tan",
            "sheng",
            "gu",
            "qiu",
            "meng",
            "long",
            "wan",
            "duan",
            "zhang",
            "qian",
            "tang",
            "yin",
            "lai",
            "chang",
        }

        # Common Korean surnames (Latin romanization)
        korean_surnames = {
            "kim",
            "lee",
            "park",
            "choi",
            "jung",
            "kang",
            "cho",
            "yoon",
            "jang",
            "lim",
            "han",
            "oh",
            "shin",
            "seo",
            "kwon",
            "song",
            "hong",
            "ahn",
            "koo",
            "moon",
            "yang",
            "baek",
            "son",
            "ha",
            "yoo",
            "nam",
            "shim",
            "noh",
            "jeong",
            "hwang",
            "cha",
            "joo",
            "ko",
            "bae",
            "heo",
            "min",
            "goh",
            "suh",
            "yim",
            "jeon",
        }

        # Check for CJK surname in tokens
        # Hybrid pattern: Anglo given name + CJK surname
        # Assume last token is surname (Western order: "Robert Chen")
        last_token = tokens[-1].lower()

        # Only trigger if we have Anglo given + CJK surname
        if has_anglo_given:
            if last_token in chinese_surnames:
                return RegionDetectionResult(
                    region_code="E1",
                    confidence=0.95,
                    detection_method="hybrid-cjk-surname",
                    metadata={
                        "given": first_token,
                        "surname": last_token,
                        "cjk_type": "chinese",
                        "reason": "CJK surname trumps Anglo given name",
                    },
                )
            elif last_token in korean_surnames:
                return RegionDetectionResult(
                    region_code="E4",
                    confidence=0.95,
                    detection_method="hybrid-cjk-surname",
                    metadata={
                        "given": first_token,
                        "surname": last_token,
                        "cjk_type": "korean",
                        "reason": "CJK surname trumps Anglo given name",
                    },
                )

        return None

    def _apply_affiliation_tiebreak(
        self, entry: Dict[str, Any], result: RegionDetectionResult
    ) -> RegionDetectionResult:
        """
        Apply affiliation tie-breaking for ambiguous family regions.

        Expert's guidance: "Use affiliation ONLY for tie-breaking within families"

        Ambiguous families:
        - {A2, G1}: Spanish names (Spain vs Latin America)
        - {E1, E2}: Chinese names (Mainland vs Taiwan/HK)
        - {C3, C4, C5}: Arabic names (Levant vs Gulf vs Maghreb)

        Args:
            entry: Name entry dict
            result: Initial detection result from priority rules

        Returns:
            Modified result if tie-break applied, otherwise original result
        """
        # Define ambiguous families
        FAMILY_TIESETS = [
            frozenset({"A2", "G1"}),  # Spanish
            frozenset({"E1", "E2"}),  # Chinese
            frozenset({"C3", "C4", "C5"}),  # Arabic
        ]

        # Check if current result is in an ambiguous family
        current_region = result.region_code
        in_family = None
        for family in FAMILY_TIESETS:
            if current_region in family:
                in_family = family
                break

        if not in_family:
            # Not ambiguous - return as-is
            return result

        # Get affiliation region
        affiliations = entry.get("Affiliations", [])
        if not affiliations:
            # No affiliation data - return as-is
            return result

        # Extract country from affiliation
        affiliation_region = None
        for affiliation in affiliations:
            if isinstance(affiliation, dict):
                country = affiliation.get("country")
                if country:
                    affiliation_region = get_region_for_territory(country)
                    break

        if not affiliation_region or affiliation_region not in in_family:
            # Affiliation not in same family - return as-is
            return result

        # Apply tie-break: use affiliation to resolve ambiguity
        return RegionDetectionResult(
            region_code=affiliation_region,
            confidence=min(0.90, result.confidence + 0.10),  # Boost confidence slightly
            detection_method=f"{result.detection_method}+affiliation-tiebreak",
            metadata={
                **result.metadata,
                "tiebreak_family": list(in_family),
                "original_region": current_region,
                "affiliation_region": affiliation_region,
                "reason": "Affiliation tie-break within ambiguous family",
            },
        )

    def _analyze_scripts(self, text: str) -> Dict[str, int]:
        """Analyze Unicode scripts in text."""
        script_counts = {}

        for char in text:
            if char.isalpha():
                # Get Unicode script
                script = self._get_unicode_script(char)
                script_counts[script] = script_counts.get(script, 0) + 1

        return script_counts

    def _get_unicode_script(self, char: str) -> str:
        """Determine Unicode script of a character."""
        # Simplified script detection - real implementation would use unicodedata
        code = ord(char)

        # Basic Latin
        if 0x0041 <= code <= 0x007A:
            return "Latin"
        # Latin Extended
        elif 0x0100 <= code <= 0x024F:
            return "Latin"
        # Cyrillic
        elif 0x0400 <= code <= 0x04FF:
            return "Cyrillic"
        # Greek
        elif 0x0370 <= code <= 0x03FF:
            return "Greek"
        # Arabic
        elif 0x0600 <= code <= 0x06FF:
            return "Arabic"
        # Hebrew
        elif 0x0590 <= code <= 0x05FF:
            return "Hebrew"
        # Devanagari
        elif 0x0900 <= code <= 0x097F:
            return "Devanagari"
        # Bengali
        elif 0x0980 <= code <= 0x09FF:
            return "Bengali"
        # Tamil
        elif 0x0B80 <= code <= 0x0BFF:
            return "Tamil"
        # Telugu
        elif 0x0C00 <= code <= 0x0C7F:
            return "Telugu"
        # Sinhala
        elif 0x0D80 <= code <= 0x0DFF:
            return "Sinhala"
        # Thai
        elif 0x0E00 <= code <= 0x0E7F:
            return "Thai"
        # Myanmar
        elif 0x1000 <= code <= 0x109F:
            return "Myanmar"
        # Georgian
        elif 0x10A0 <= code <= 0x10FF:
            return "Georgian"
        # Hangul
        elif 0xAC00 <= code <= 0xD7AF or 0x1100 <= code <= 0x11FF:
            return "Hangul"
        # CJK
        elif 0x4E00 <= code <= 0x9FFF or 0x3400 <= code <= 0x4DBF:
            return "CJK"
        # Hiragana/Katakana
        elif 0x3040 <= code <= 0x309F or 0x30A0 <= code <= 0x30FF:
            return "CJK"
        # Armenian
        elif 0x0530 <= code <= 0x058F:
            return "Armenian"
        # Ethiopic
        elif 0x1200 <= code <= 0x137F:
            return "Ethiopic"
        else:
            return "Unknown"

    def _init_surname_patterns(self):
        """Initialize surname pattern databases for implemented regions only."""
        self.surname_patterns = {}

        # Only add patterns for implemented regions
        if "A1" in self.IMPLEMENTED_REGIONS:
            self.surname_patterns["A1"] = {
                # Common Anglo surnames
                "smith",
                "johnson",
                "williams",
                "brown",
                "jones",
                "garcia",
                "miller",
                "davis",
                "rodriguez",
                "martinez",
                "hernandez",
                "lopez",
                "gonzalez",
                "wilson",
                "anderson",
                "thomas",
                "taylor",
                "moore",
                "jackson",
                "martin",
                "lee",
                "perez",
                "thompson",
                "white",
                "harris",
                "sanchez",
                "clark",
                # Mathematician surnames
                "newton",
                "darwin",
                "maxwell",
                "faraday",
                "kelvin",
                "rayleigh",
                "hardy",
                "littlewood",
                "ramsey",
                "turing",
                "russell",
                "whitehead",
                "hamilton",
                "cayley",
                "sylvester",
                "boole",
                "de morgan",
                "babbage",
                "lovelace",
            }

        if "A2" in self.IMPLEMENTED_REGIONS:
            self.surname_patterns["A2"] = {
                # German
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
                "bauer",
                "richter",
                "gauss",
                "riemann",
                "hilbert",
                "weierstrass",
                "cantor",
                "dedekind",
                "kronecker",
                "kummer",
                "dirichlet",
                "jacobi",
                "weyl",
                "noether",
                "artin",
                "hasse",
                "hecke",
                "minkowski",
                "hurwitz",
                "landau",
                "siegel",
                "selberg",
                "einstein",
                "planck",
                "heisenberg",
                "schrödinger",
                "born",
                "bohr",
                # French
                "bernard",
                "dubois",
                "thomas",
                "robert",
                "richard",
                "petit",
                "durand",
                "cauchy",
                "lagrange",
                "laplace",
                "fourier",
                "poisson",
                "hermite",
                "poincaré",
                "hadamard",
                "lebesgue",
                "borel",
                "cartan",
                "weil",
                "serre",
                "grothendieck",
                "deligne",
                "connes",
                "villani",
                "demailly",
                # Dutch
                "van der waals",
                "lorentz",
                "zeeman",
                "kamerlingh",
                "huygens",
                "stevin",
                "van der waerden",
                "brouwer",
                "de groot",
                # Belgian
                "deligne",
                "bourgain",
                "daubechies",
                # Austrian
                "schrödinger",
                "pauli",
                "mach",
                "boltzmann",
                "doppler",
                "gödel",
                # Swiss
                "euler",
                "bernoulli",
                "steiner",
                # Italian (Northern)
                "rossi",
                "ferrari",
                "russo",
                "bianchi",
                "romano",
                "colombo",
                "ricci",
                "fibonacci",
                "galilei",
                "torricelli",
                "volta",
                "avogadro",
                "fermi",
                "levi-civita",
                "ricci-curbastro",
                "betti",
                "cremona",
                "peano",
                "bombieri",
                "fubini",
                "vitali",
                # Hungarian
                "nagy",
                "kovács",
                "tóth",
                "szabó",
                "horváth",
                "varga",
                "kiss",
                "molnár",
                "németh",
                "farkas",
                "balogh",
                "papp",
                "takács",
                "juhász",
                "neumann",
                "wigner",
                "teller",
                "kármán",
                "pólya",
                "szegő",
                "riesz",
                "haar",
                "turán",
                "rényi",
                "lovász",
                "szemerédi",
                "babai",
                # Polish mathematicians
                "banach",
                "steinhaus",
                "mazur",
                "schauder",
                "kuratowski",
                "sierpiński",
                "tarski",
                "mostowski",
                "knaster",
                "borsuk",
                "ulam",
                "zygmund",
            }

        if "A3" in self.IMPLEMENTED_REGIONS:
            self.surname_patterns["A3"] = {
                # Swedish
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
                # Norwegian
                "hansen",
                "johansen",
                "olsen",
                "larsen",
                "andersen",
                "pedersen",
                "nielsen",
                "kristiansen",
                "jensen",
                "carlsen",
                "lie",
                "abel",
                # Danish
                "nielsen",
                "jensen",
                "hansen",
                "pedersen",
                "andersen",
                "christensen",
                "larsen",
                "sørensen",
                "rasmussen",
                "jørgensen",
                "petersen",
                "madsen",
                # Icelandic (patronymic)
                "einarsson",
                "sigurdsson",
                "guðmundsson",
                "jónsson",
                "ólafsson",
                "magnusson",
                "þórsson",
                "ragnarsson",
                "björnsson",
                "stefánsson",
                # Finnish
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
                "saarinen",
                # Estonian
                "tamm",
                "saar",
                "mägi",
                "kask",
                "kukk",
                "sepp",
                "kõiv",
                "rebane",
                "hunt",
                "roos",
                "vaher",
                "männik",
                "kadak",
                "kallas",
                # Latvian
                "bērziņš",
                "kalniņš",
                "ozoliņš",
                "liepiņš",
                "vilks",
                "priede",
                "krūmiņš",
                "jansons",
                "pētersons",
                "kļaviņš",
                # Lithuanian
                "kazlauskas",
                "petrauskas",
                "stankevičius",
                "jankauskas",
                "žukauskas",
                "butkus",
                "paulauskas",
                "gudauskas",
                "mockus",
                "rimkus",
                # Hungarian (mathematicians and common surnames)
                "erdős",
                "rényi",
                "turán",
                "kövári",
                "szekeres",
                "lovász",
                "szemerédi",
                "babai",
                "bollobás",
                "komlós",
                "rödl",
                "freud",
                "katona",
                "simonovits",
                "nagy",
                "kovács",
                "tóth",
                "szabó",
                "horváth",
                "varga",
                "kiss",
                "molnár",
            }

        if "B1" in self.IMPLEMENTED_REGIONS:
            self.surname_patterns["B1"] = {
                # Russian
                "ivanov",
                "smirnov",
                "kuznetsov",
                "popov",
                "sokolov",
                "lebedev",
                "kozlov",
                "novikov",
                "morozov",
                "petrov",
                "volkov",
                "solovyov",
                "vasilyev",
                "zaytsev",
                "pavlov",
                "semyonov",
                "golubev",
                "vinogradov",
                "chebyshev",
                "lobachevsky",
                "markov",
                "lyapunov",
                "kolmogorov",
                "khinchin",
                "alexandrov",
                "pontryagin",
                "shafarevich",
                "gel'fand",
                "arnol'd",
                "sinai",
                "novikov",
                "manin",
                "kirillov",
                "faddeev",
                "putin",
                "medvedev",
                "gorbachev",
                "yeltsin",
                "brezhnev",
                "khrushchev",
                # Ukrainian
                "shevchenko",
                "bondarenko",
                "kovalenko",
                "tkachenko",
                "kravchenko",
                "oliynyk",
                "kovalchuk",
                "shevchuk",
                "polishchuk",
                "bondarchuk",
                "zelensky",
                "poroshenko",
                "yanukovych",
                "yushchenko",
                "kuchma",
            }

        if "B2" in self.IMPLEMENTED_REGIONS:
            self.surname_patterns["B2"] = {
                # Polish
                "nowak",
                "kowalski",
                "wiśniewski",
                "wójcik",
                "kowalczyk",
                "kamiński",
                "lewandowski",
                "zieliński",
                "szymański",
                "woźniak",
                "dąbrowski",
                "kozłowski",
                "jankowski",
                "mazur",
                "wojciechowski",
                "kwiatkowski",
                "krawczyk",
                "kaczmarek",
                "piotrowski",
                "grabowski",
                # Czech
                "novák",
                "svoboda",
                "novotný",
                "dvořák",
                "černý",
                "procházka",
                "krejčí",
                "čech",
                "bolzano",
                # Slovak
                "kováč",
                "horváth",
                "baláž",
                "szabó",
                "molnár",
                "lukáč",
                "kováčik",
                # Croatian
                "horvat",
                "kovačić",
                "babić",
                "marić",
                "jurić",
                "pavlović",
                "kovač",
                "božić",
                "mohorovičić",
                # Serbian
                "jovanović",
                "petrović",
                "nikolić",
                "marković",
                "đorđević",
                "stojanović",
                "milić",
                "milanković",
                # Slovenian
                "novak",
                "horvat",
                "krajnc",
                "kovač",
                "potočnik",
                "vidmar",
            }

        if "B3" in self.IMPLEMENTED_REGIONS:
            self.surname_patterns["B3"] = {
                # Ancient Greek mathematicians
                "euclid",
                "archimedes",
                "apollonius",
                "diophantus",
                "pappus",
                "ptolemy",
                "thales",
                "pythagoras",
                "eratosthenes",
                "hipparchus",
                "menelaus",
                # Modern Greek surnames
                "papadopoulos",
                "georgiou",
                "dimitriou",
                "ioannou",
                "constantinou",
                "nikolaou",
                "christou",
                "michail",
                "stavros",
                "kostas",
                "yannis",
                "christodoulou",
                "papageorgiou",
                "hadjidakis",
                "chatzidakis",
                # Common patterns (-opoulos, -akis, -ou)
                "antonopoulos",
                "giannopoulos",
                "economopoulos",
                "theodoropoulos",
                "stefanakis",
                "nikolakis",
                "dimitrakis",
                "georgakis",
                "christakis",
                # Greek script versions (for mixed detection)
                "παπαδόπουλος",
                "γεωργίου",
                "δημητρίου",
                "ιωάννου",
                "κωνσταντίνου",
                "νικολάου",
                "χρήστου",
                "μιχαήλ",
                "σταύρος",
                "κώστας",
                "γιάννης",
            }

        if "C2" in self.IMPLEMENTED_REGIONS:
            self.surname_patterns["C2"] = {
                # Persian
                "ahmadi",
                "hosseini",
                "mohammadi",
                "rezaei",
                "karimi",
                "moradi",
                "ali",
                "rahimi",
                "rostami",
                "nazari",
                "safari",
                "hashemi",
                "khayyam",
                "tusi",
                "kashani",
                "biruni",
                "khwarizmi",
                "karaji",
                # Tajik
                "rahmonov",
                "safarov",
                "karimov",
                "nazarov",
                "rustamov",
            }

        if "C3" in self.IMPLEMENTED_REGIONS:
            self.surname_patterns["C3"] = {
                # Arabic (Levant/Egypt)
                "hassan",
                "hussein",
                "ahmad",
                "mahmoud",
                "ibrahim",
                "mohamed",
                "abdullah",
                "yousef",
                "khalil",
                "rahman",
                "hamza",
                "omar",
                "saleh",
                "saeed",
                "nasser",
                "jaber",
                "haddad",
                "khoury",
                "al-khwarizmi",
                "alhazen",
                "al-kindi",
                "al-battani",
                "al-biruni",
                "al-kashi",
                "al-tusi",
                "al-din",
                "al-jazari",
                "al-qalasadi",
                # Add more Arabic patterns without hyphen
                "muhammad",
                "khwarizmi",
                "alkhwarizmi",
                "jabir",
                "aljabir",
                "sina",
                "farabi",
                "alfarabi",
            }

        if "C4" in self.IMPLEMENTED_REGIONS:
            self.surname_patterns["C4"] = {
                # Gulf Arabic
                "al-rashid",
                "al-sabah",
                "al-thani",
                "al-nahyan",
                "al-maktoum",
                "al-khalifa",
                "al-said",
                "al-otaibi",
                "al-mutairi",
                "al-harbi",
                "al-ghamdi",
                "al-qahtani",
                "al-shammari",
                "al-anazi",
                "al-tamimi",
            }

        if "D1" in self.IMPLEMENTED_REGIONS:
            self.surname_patterns["D1"] = {
                # Hindi Belt
                "sharma",
                "verma",
                "gupta",
                "kumar",
                "singh",
                "yadav",
                "mishra",
                "pandey",
                "patel",
                "tiwari",
                "jain",
                "agarwal",
                "mehta",
                "joshi",
                "chauhan",
                "gautam",
                "kaur",
                "malhotra",
                "kapoor",
                "chopra",
                "ramanujan",
                "bose",
                "chandrasekhar",
                "raman",
                "saha",
                "mahalanobis",
                "rao",
                "bhattacharya",
                "das",
                "sen",
                "mukherjee",
                "chatterjee",
            }

        if "E1" in self.IMPLEMENTED_REGIONS:
            self.surname_patterns["E1"] = {
                # Chinese (Mainland)
                "wang",
                "li",
                "zhang",
                "liu",
                "chen",
                "yang",
                "huang",
                "zhao",
                "zhou",
                "wu",
                "xu",
                "sun",
                "ma",
                "zhu",
                "hu",
                "guo",
                "he",
                "lin",
                "luo",
                "gao",
                "zheng",
                "liang",
                "xie",
                "song",
                "tang",
                "chern",
                "yau",
                "tao",
                "hua",
                "shen",
                "feng",
                "cao",
                "deng",
            }

        if "E3" in self.IMPLEMENTED_REGIONS:
            self.surname_patterns["E3"] = {
                # Japanese
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
                "saito",
                "matsumoto",
                "inoue",
                "kimura",
                "hayashi",
                "shimizu",
                "yamazaki",
                "mori",
                "abe",
                "ikeda",
                "hashimoto",
                "yamashita",
                "ishikawa",
                "nakajima",
                "maeda",
                "fujita",
                "kiyoshi",
                "kunihiko",
                "shigefumi",
                "heisuke",
                "goro",
                "mikio",
            }

        if "G1" in self.IMPLEMENTED_REGIONS:
            self.surname_patterns["G1"] = {
                # Spanish
                "garcía",
                "rodríguez",
                "gonzález",
                "fernández",
                "lópez",
                "martínez",
                "sánchez",
                "pérez",
                "gómez",
                "ruiz",
                "hernández",
                "jiménez",
                "díaz",
                "moreno",
                "muñoz",
                "álvarez",
                "romero",
                "navarro",
                "torres",
                "domínguez",
                "vázquez",
                "ramos",
                "castro",
                "ortiz",
                # Portuguese
                "silva",
                "santos",
                "oliveira",
                "souza",
                "rodrigues",
                "almeida",
                "nascimento",
                "lima",
                "araújo",
                "fernandes",
                "carvalho",
                "gomes",
                "martins",
                "rocha",
                "ribeiro",
                "alves",
                "monteiro",
                "mendes",
                "barros",
                "freitas",
                "barbosa",
                "pinto",
                "moreira",
                "cavalcanti",
                # Latin American
                "garcia",
                "rodriguez",
                "gonzalez",
                "fernandez",
                "lopez",
                "martinez",
                "sanchez",
                "perez",
                "gomez",
                "ruiz",
                "hernandez",
                "jimenez",
                "diaz",
                "moreno",
                "munoz",
                "alvarez",
                "romero",
                "navarro",
            }

        if "E4" in self.IMPLEMENTED_REGIONS:
            self.surname_patterns["E4"] = {
                # Most common Korean surnames
                "kim",
                "lee",
                "park",
                "choi",
                "jung",
                "kang",
                "cho",
                "yoon",
                "jang",
                "lim",
                "han",
                "oh",
                "seo",
                "shin",
                "kwon",
                "hwang",
                "ahn",
                "song",
                "yoo",
                "hong",
                "jeon",
                "go",
                "moon",
                "yang",
                "baek",
                "heo",
                "nam",
                "sim",
                "won",
                "kwak",
                "son",
                "myung",
                "noh",
                "koo",
                "ryu",
                "jin",
                "ma",
                "cha",
                "yu",
                "do",
                "bae",
                "seok",
                "woo",
                "min",
                "gang",
                "ko",
                "goo",
                "tae",
                "pyo",
                "ha",
                "roh",
                "rhee",
                "yeon",
                "cha",
                "bang",
                "ki",
                "jeong",
                "chae",
                "chun",
                # Mathematician surnames
                "kim",
                "lee",
                "park",
                "choi",
                "cho",
                "kang",
                "moon",
                "seo",
                "han",
                "shin",
                "kwon",
                "jung",
                "oh",
                "yoon",
                "jang",
                "hwang",
                "song",
                "ahn",
                "lim",
                "hong",
                # Romanization variants
                "gim",
                "ri",
                "bak",
                "choe",
                "jeong",
                "gang",
                "jo",
                "yun",
                "jang",
                "im",
            }

    def _detect_by_surname_patterns(
        self, name: str, possible_regions: List[str]
    ) -> Optional[str]:
        """Detect region using surname pattern matching."""
        if not hasattr(self, "surname_patterns"):
            return None

        # Extract surname from "Family, Given" format
        if "," in name:
            family_name = name.split(",")[0].strip().lower()
        else:
            # For Asian names, check if first part is a known surname
            parts = name.strip().split()
            if len(parts) >= 2:
                # Check if first part is an Asian surname (E1, E3, E4 regions)
                first_part = parts[0].lower()
                first_part_clean = self._clean_surname_for_matching(first_part)

                # Check if it's a known Asian surname
                is_asian_surname = False
                for region_code in ["E1", "E3", "E4"]:
                    if (
                        region_code in self.surname_patterns
                        and region_code in self.IMPLEMENTED_REGIONS
                    ):
                        if first_part_clean in self.surname_patterns[region_code]:
                            is_asian_surname = True
                            break

                # Check if the first name is clearly Western
                is_western_given = self._is_western_given_name(parts[0])

                if is_asian_surname and not is_western_given:
                    family_name = first_part_clean
                elif is_western_given:
                    # Western format: "Given Family" - even if surname is Asian
                    # For Western given names, prioritize Western regions
                    western_regions = [
                        r
                        for r in possible_regions
                        if r.startswith("A") or r.startswith("G")
                    ]
                    if western_regions:
                        return western_regions[0]
                    family_name = parts[-1].lower()
                else:
                    # Western format: "Given Family"
                    family_name = parts[-1].lower()
            else:
                return None

        # Clean surname for matching
        family_name = self._clean_surname_for_matching(family_name)

        # Score each possible region based on surname matches
        region_scores = {}

        for region in possible_regions:
            if region in self.surname_patterns and region in self.IMPLEMENTED_REGIONS:
                surnames = self.surname_patterns[region]

                # Direct match
                if family_name in surnames:
                    region_scores[region] = 10
                else:
                    # Partial match scoring
                    for surname in surnames:
                        if family_name.startswith(surname) or surname.startswith(
                            family_name
                        ):
                            region_scores[region] = max(region_scores.get(region, 0), 7)
                        elif len(surname) >= 3 and (
                            _wb(surname).search(family_name)
                            or _wb(family_name).search(surname)
                        ):
                            region_scores[region] = max(region_scores.get(region, 0), 5)

        # Return region with highest score (minimum score of 7 to avoid false positives)
        if region_scores:
            # Find all regions with the highest score
            max_score = max(region_scores.values())
            if max_score >= 7:
                top_regions = [r for r, s in region_scores.items() if s == max_score]

                # If there's only one top region, return it
                if len(top_regions) == 1:
                    return top_regions[0]

                # Disambiguation for tied scores
                # Check for East Asian name patterns (hyphenated given names)
                remaining_name = name.replace(family_name, "", 1).strip()
                if remaining_name:
                    # Korean names often have hyphenated given names
                    if "-" in remaining_name and "E4" in top_regions:
                        return "E4"
                    # Check for Korean given name patterns (2-3 syllables)
                    if "E4" in top_regions and len(remaining_name.split("-")) in [2, 3]:
                        return "E4"

                # Default: prefer non-English for ambiguous Asian surnames
                if "lee" in family_name.lower() and "E4" in top_regions:
                    return "E4"

                # Otherwise return the first match
                return top_regions[0]

        return None

    def _is_western_given_name(self, name: str) -> bool:
        """Check if a name is a common Western given name."""
        western_given_names = {
            "john",
            "james",
            "robert",
            "michael",
            "william",
            "david",
            "richard",
            "thomas",
            "christopher",
            "charles",
            "daniel",
            "matthew",
            "anthony",
            "mark",
            "donald",
            "steven",
            "paul",
            "andrew",
            "joshua",
            "kenneth",
            "kevin",
            "brian",
            "george",
            "edward",
            "ronald",
            "timothy",
            "jason",
            "jeffrey",
            "ryan",
            "jacob",
            "gary",
            "nicholas",
            "eric",
            "jonathan",
            "stephen",
            "larry",
            "justin",
            "scott",
            "brandon",
            "benjamin",
            "samuel",
            "gregory",
            "alexander",
            "patrick",
            "frank",
            "raymond",
            "jack",
            "dennis",
            "jerry",
            "tyler",
            "aaron",
            "jose",
            "henry",
            "adam",
            "douglas",
            "peter",
            "zachary",
            "noah",
            "walter",
            "christian",
            "javier",
            "harold",
            "arthur",
            # Common female names
            "mary",
            "patricia",
            "jennifer",
            "linda",
            "elizabeth",
            "barbara",
            "susan",
            "jessica",
            "sarah",
            "karen",
            "nancy",
            "lisa",
            "betty",
            "helen",
            "sandra",
            "donna",
            "carol",
            "ruth",
            "sharon",
            "michelle",
            "laura",
            "sarah",
            "kimberly",
            "deborah",
            "dorothy",
            "lisa",
            "nancy",
            "karen",
            "betty",
            "helen",
            "sandra",
            "donna",
            "carol",
            "ruth",
            "sharon",
            "michelle",
            "laura",
            "emily",
            "kimberly",
            "deborah",
            "dorothy",
            "amy",
            "angela",
            "ashley",
            "brenda",
            "emma",
            "olivia",
            "cynthia",
            "marie",
            "janet",
            "catherine",
            "frances",
            "christine",
            "samantha",
            "debra",
            "rachel",
            "carolyn",
            "janet",
            "virginia",
            "maria",
            "heather",
            "diane",
            "julie",
            "joyce",
            "victoria",
            "kelly",
            "christina",
            "joan",
            "evelyn",
            "judith",
            "megan",
            "cheryl",
            "andrea",
            "hannah",
            "jacqueline",
            "martha",
            "gloria",
            "teresa",
        }
        return name.lower().strip() in western_given_names

    def _clean_surname_for_matching(self, surname: str) -> str:
        """Clean surname by removing common particles and prefixes."""
        # Remove common particles (case insensitive)
        particles = {
            "de",
            "del",
            "della",
            "delle",
            "dello",
            "di",
            "da",
            "dal",
            "dalla",
            "du",
            "des",
            "le",
            "la",
            "les",
            "dos",
            "das",
            "do",
            "da",
            "von",
            "van",
            "der",
            "den",
            "het",
            "ten",
            "ter",
            "te",
            "zum",
            "zur",
            "am",
            "im",
            "zu",
            "auf",
            "unter",
            "al",
            "ibn",
            "abu",
            "bin",
            "ben",
            "bat",
            "o'",
            "mc",
            "mac",
            "fitz",
        }

        # Split on spaces and hyphens
        parts = surname.replace("-", " ").split()
        if len(parts) > 1:
            # Check if first part is a particle
            if parts[0].lower() in particles:
                return " ".join(parts[1:])
            # Check if it starts with particle patterns
            for particle in particles:
                if surname.startswith(particle.lower() + " "):
                    return surname[len(particle) + 1 :]

        return surname

    def _load_regions(self):
        """Load and register only actually implemented region implementations."""
        import importlib

        # Load all V7 regions that have processor implementations
        region_imports = {
            # A-groups (Anglo-sphere/Western)
            "A1": ("src.regions.a_groups.a1_anglo_sphere", "A1_AngloSphere"),
            "A2": ("src.regions.a_groups.a2_western_europe", "A2_WesternEurope"),
            "A3": (
                "src.regions.a_groups.a3_nordic_baltic.processor",
                "A3NordicBalticProcessor",
            ),
            "A4": ("src.regions.a_groups.a4_oceania.processor", "A4OceaniaProcessor"),
            "A5": (
                "src.regions.a_groups.a5_caribbean.processor",
                "A5CaribbeanProcessor",
            ),
            # B-groups (Slavic)
            "B1": ("src.regions.b_groups.b1_east_slavic", "B1_EastSlavic"),
            "B2": (
                "src.regions.b_groups.b2_south_slavic_central",
                "B2_SouthSlavicCentral",
            ),
            "B3": ("src.regions.b_groups.b3_greek.processor", "B3GreekProcessor"),
            # C-groups (Middle East/Turkic)
            "C1": ("src.regions.c_groups.c1_turkic.processor", "C1TurkicProcessor"),
            "C2": ("src.regions.c_groups.c2_persian_tajik", "C2_PersianTajik"),
            "C3": ("src.regions.c_groups.c3_arabic_levant_nile", "C3_ArabicLevantNile"),
            "C4": ("src.regions.c_groups.c4_arabic_gulf", "C4_ArabicGulf"),
            "C5": (
                "src.regions.c_groups.c5_arabic_maghreb.processor",
                "C5_ArabicMaghreb",
            ),
            "C6": (
                "src.regions.c_groups.c6_hebrew_diaspora.processor",
                "C6_HebrewDiaspora",
            ),
            "C7": ("src.regions.c_groups.c7_armenian.processor", "C7_Armenian"),
            "C8": ("src.regions.c_groups.c8_georgian.processor", "C8_Georgian"),
            "C9": (
                "src.regions.c_groups.c9_caucasus_turkic.processor",
                "C9_CaucasusTurkic",
            ),
            # D-groups (South Asia)
            "D1": (
                "src.regions.d_groups.d1_south_asia_hindi_belt",
                "D1_SouthAsiaHindiBelt",
            ),
            "D2": (
                "src.regions.d_groups.d2_south_asia_dravidian.processor",
                "D2_SouthAsiaDravidian",
            ),
            "D3": (
                "src.regions.d_groups.d3_south_asia_bengali.processor",
                "D3_SouthAsiaBengali",
            ),
            "D4": (
                "src.regions.d_groups.d4_pakistan_urdu.processor",
                "D4_PakistanUrdu",
            ),
            "D5": ("src.regions.d_groups.d5_sinhala.processor", "D5_Sinhala"),
            # E-groups (East Asia)
            "E1": (
                "src.regions.e_groups.e1_sinophone_mainland",
                "E1_SinophoneMainland",
            ),
            "E2": (
                "src.regions.e_groups.e2_traditional_chinese.processor",
                "E2_TraditionalChinese",
            ),
            "E3": ("src.regions.e_groups.e3_japan", "E3_Japan"),
            "E4": ("src.regions.e_groups.e4_korea.processor", "E4KoreanProcessor"),
            "E5": ("src.regions.e_groups.e5_vietnam.processor", "E5_Vietnam"),
            "E6": ("src.regions.e_groups.e6_mainland_sea.processor", "E6_MainlandSEA"),
            "E7": (
                "src.regions.e_groups.e7_maritime_sea.processor",
                "E7MaritimeSEAProcessor",
            ),
            # F-groups (Africa)
            "F1": (
                "src.regions.f_groups.f1_ssa_francophone.processor",
                "F1_SSAFrancophone",
            ),
            "F2": (
                "src.regions.f_groups.f2_ssa_anglophone.processor",
                "F2_SSAAnglophone",
            ),
            "F3": (
                "src.regions.f_groups.f3_horn_of_africa.processor",
                "F3_HornOfAfrica",
            ),
            "F4": (
                "src.regions.f_groups.f4_lusophone_africa.processor",
                "F4_LusophoneAfrica",
            ),
            # G-groups (Latin America)
            "G1": ("src.regions.g_groups.g1_latin_america", "G1_LatinAmerica"),
            # Special groups
            "H1": ("src.regions.special.h1_historical.processor", "H1_Historical"),
            "R0": (
                "src.regions.special.r0_residual_latin_ascii.processor",
                "R0_ResidualLatinAscii",
            ),
            "Z0": ("src.regions.special.z0_quarantine.processor", "Z0_Quarantine"),
        }

        regions_loaded = 0

        for region_code in self.IMPLEMENTED_REGIONS:
            if region_code in region_imports:
                module_path, class_name = region_imports[region_code]
                try:
                    # Import the module
                    module = importlib.import_module(module_path)

                    # Get the class
                    region_class = getattr(module, class_name)

                    # Instantiate the region
                    region_instance = region_class()

                    # Register the region
                    self.register_region(region_instance)
                    regions_loaded += 1

                except Exception as e:
                    logger.error(
                        f"Could not load region {region_code} from {module_path}: {e}"
                    )

        logger.info(f"Loaded {regions_loaded} implemented regions successfully")
