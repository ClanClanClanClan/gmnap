"""
Comprehensive region detection accuracy tests for ALL 37 regions.

740+ parametrized test cases covering:
- Common surnames (top 5 per country)
- Rare/unusual surnames
- Diaspora / ambiguous names
- Compound / hyphenated names
- Names with diacritics
- Short names (2-3 chars)
- Transliterated names (Cyrillic/Arabic/CJK in Latin)
- Female variants (-ova, -ova, -ska, etc.)

Every region has 15-25 entries.  Country codes drive the expected result
because the production detector treats CountryCodes as highest priority.
"""

from __future__ import annotations

import pytest


@pytest.fixture(scope="module")
def manager():
    import sys

    sys.path.insert(0, ".")
    from src.regions.manager_optimized import RegionManager

    return RegionManager()


# ---------------------------------------------------------------------------
# Master test-case table
# Format: (canonical_latin, country_codes, expected_region, description)
# ---------------------------------------------------------------------------

REGION_TEST_CASES = [
    # ======================================================================
    # A1 - Anglo-Sphere (US, GB, AU, CA, NZ, IE, ZA equivalents)
    # ======================================================================
    ("Smith, John", ["US"], "A1", "Most common US surname"),
    ("Johnson, Emily", ["US"], "A1", "Second most common US surname"),
    ("Williams, David", ["US"], "A1", "Third most common US surname"),
    ("Brown, Michael", ["GB"], "A1", "Common British surname"),
    ("Jones, Catherine", ["GB"], "A1", "Common Welsh-origin surname"),
    ("Wilson, Robert", ["CA"], "A1", "Common Canadian surname"),
    ("Taylor, James", ["AU"], "A1", "Common Australian surname"),
    ("Anderson, Craig", ["NZ"], "A1", "Common NZ surname"),
    ("Thomas, Dylan", ["GB"], "A1", "Welsh poet surname"),
    ("Jackson, Andrew", ["US"], "A1", "US presidential surname"),
    ("White, Patrick", ["AU"], "A1", "Australian Nobel laureate"),
    ("Harris, Kamala", ["US"], "A1", "Compound heritage, US CC"),
    ("Martin, Steve", ["US"], "A1", "Ambiguous with French, US CC resolves"),
    ("Thompson, Emma", ["GB"], "A1", "British actress surname"),
    ("Garcia, Maria", ["US"], "A1", "Hispanic surname in US context"),
    ("O'Brien, Conan", ["IE"], "A1", "Irish compound surname"),
    ("MacDonald, John", ["CA"], "A1", "Scottish-Canadian compound"),
    ("Campbell, Naomi", ["GB"], "A1", "Scottish-origin surname"),
    ("Murphy, Cillian", ["IE"], "A1", "Common Irish surname"),
    ("O'Sullivan, Sonia", ["IE"], "A1", "Irish compound with apostrophe"),
    ("McGregor, Ewan", ["GB"], "A1", "Scottish Mc- prefix"),
    ("Singh, Harjit", ["CA"], "A1", "Sikh name in Canadian context"),
    ("Li, Fei-Fei", ["US"], "A1", "Chinese diaspora name in US"),
    ("Lee, Bruce", ["US"], "A1", "Ambiguous Lee, US CC resolves to A1"),
    ("Ng, Andrew", ["US"], "A1", "Short Chinese-origin surname in US"),
    # ======================================================================
    # A2 - Western Europe (DE, FR, IT, NL, BE, AT, CH, ES, PT, LU)
    # ======================================================================
    ("Muller, Hans", ["DE"], "A2", "Most common German surname (ASCII)"),
    ("Schmidt, Helmut", ["DE"], "A2", "Second most common German"),
    ("Schneider, Maria", ["DE"], "A2", "Third most common German"),
    ("Fischer, Bobby", ["DE"], "A2", "German surname (chess player from US)"),
    ("Weber, Max", ["DE"], "A2", "Famous sociologist surname"),
    ("Meyer, Ursula", ["DE"], "A2", "Common German variant of Meier"),
    ("Dupont, Pierre", ["FR"], "A2", "Common French surname"),
    ("Martin, Jean-Pierre", ["FR"], "A2", "Most common French surname"),
    ("Bernard, Claude", ["FR"], "A2", "French physiologist surname"),
    ("Rossi, Paolo", ["IT"], "A2", "Most common Italian surname"),
    ("Ferrari, Enzo", ["IT"], "A2", "Famous Italian surname"),
    ("de Vries, Hugo", ["NL"], "A2", "Dutch particle surname"),
    ("van den Berg, Pieter", ["NL"], "A2", "Dutch double particle"),
    ("Gruber, Franz", ["AT"], "A2", "Common Austrian surname"),
    ("Bauer, Leopold", ["AT"], "A2", "Austrian surname"),
    ("Poincare, Henri", ["FR"], "A2", "Famous French mathematician"),
    ("Lebesgue, Henri", ["FR"], "A2", "French mathematician"),
    ("Galois, Evariste", ["FR"], "A2", "French mathematician"),
    ("Fibonacci, Leonardo", ["IT"], "A2", "Italian mathematician"),
    ("Grothendieck, Alexander", ["FR"], "A2", "German-origin in France"),
    ("van der Waerden, Bartel", ["NL"], "A2", "Dutch compound surname"),
    ("Noether, Emmy", ["DE"], "A2", "Female German mathematician"),
    ("Germain, Sophie", ["FR"], "A2", "French female mathematician"),
    ("Garcia Lopez, Antonio", ["ES"], "A2", "Spanish compound surname"),
    ("da Silva, Antonio", ["PT"], "A2", "Portuguese particle surname"),
    # ======================================================================
    # A3 - Nordic-Baltic (SE, NO, DK, FI, IS, LT, LV, EE)
    # ======================================================================
    ("Lindqvist, Sven", ["SE"], "A3", "Swedish surname"),
    ("Johansson, Scarlett", ["SE"], "A3", "Common Swedish -sson"),
    ("Hansen, Niels", ["DK"], "A3", "Common Danish surname"),
    ("Andersen, Hans Christian", ["DK"], "A3", "Famous Danish -sen"),
    ("Nielsen, Harald", ["DK"], "A3", "Common Danish surname"),
    ("Virtanen, Matti", ["FI"], "A3", "Most common Finnish surname"),
    ("Niemi, Antti", ["FI"], "A3", "Common Finnish surname"),
    ("Jonsson, Bjarni", ["IS"], "A3", "Icelandic patronymic"),
    ("Sigurdsson, Jon", ["IS"], "A3", "Icelandic patronymic"),
    ("Kazlauskas, Vytautas", ["LT"], "A3", "Most common Lithuanian"),
    ("Berzins, Janis", ["LV"], "A3", "Common Latvian surname"),
    ("Tamm, Igor", ["EE"], "A3", "Estonian physicist surname"),
    ("Svensson, Ulf", ["SE"], "A3", "Common Swedish -sson"),
    ("Eriksson, Stig", ["SE"], "A3", "Swedish patronymic"),
    ("Larsson, Stieg", ["SE"], "A3", "Swedish author surname"),
    ("Makinen, Tommi", ["FI"], "A3", "Finnish surname (ASCII)"),
    ("Laine, Eino", ["FI"], "A3", "Finnish surname"),
    ("Rasmussen, Anders", ["DK"], "A3", "Danish -sen surname"),
    ("Gustafsson, Bo", ["SE"], "A3", "Swedish -sson"),
    ("Kalninsh, Arvids", ["LV"], "A3", "Latvian surname (ASCII)"),
    # ======================================================================
    # A4 - Oceania Island States (FJ, PG, SB, VU, WS, TO)
    # ======================================================================
    ("Mataafa, Tui", ["WS"], "A4", "Samoan chiefly surname"),
    ("Taufa, Sione", ["TO"], "A4", "Tongan surname"),
    ("Ngata, Apirana", ["FJ"], "A4", "Maori-origin surname with Fiji CC"),
    ("Savea, Julian", ["WS"], "A4", "Samoan surname"),
    ("Tagaloa, Manu", ["WS"], "A4", "Samoan mythological surname"),
    ("Fonoti, Lome", ["WS"], "A4", "Samoan surname"),
    ("Vunipola, Mako", ["TO"], "A4", "Tongan surname"),
    ("Fifita, Taniela", ["TO"], "A4", "Tongan surname"),
    ("Taumoepeau, Amelia", ["TO"], "A4", "Tongan compound surname"),
    ("Koloamatangi, Sione", ["TO"], "A4", "Long Tongan surname"),
    ("Rangi, Te Ata", ["FJ"], "A4", "Polynesian given + surname"),
    ("Moana, Ratu", ["FJ"], "A4", "Fijian name"),
    ("Tui, Mere", ["FJ"], "A4", "Short Fijian surname"),
    ("Pule, Tala", ["WS"], "A4", "Short Samoan surname"),
    ("Faleolo, Sefa", ["WS"], "A4", "Samoan surname"),
    # ======================================================================
    # A5 - Dutch/French Caribbean (CW, SX, MQ, GP, GF)
    # ======================================================================
    ("Joseph, Marcus", ["CW"], "A5", "Caribbean surname"),
    ("Pierre, Jean-Claude", ["MQ"], "A5", "Martiniquais French name"),
    ("Louison, Marie", ["GP"], "A5", "Guadeloupean surname"),
    ("Celestin, Andre", ["GF"], "A5", "French Guianese surname"),
    ("Baptiste, Yves", ["MQ"], "A5", "Caribbean French surname"),
    ("Beaumont, Claire", ["MQ"], "A5", "French Caribbean surname"),
    ("Martina, Ergilio", ["CW"], "A5", "Dutch Caribbean surname"),
    ("Provence, Alain", ["GP"], "A5", "Guadeloupean surname"),
    ("Holder, Ruud", ["CW"], "A5", "Dutch Caribbean surname"),
    ("Lallement, Pierre", ["MQ"], "A5", "French name in Caribbean CC"),
    ("Rijkaard, Daniel", ["SX"], "A5", "Dutch Caribbean surname"),
    ("Giraud, Philippe", ["GP"], "A5", "Guadeloupean French surname"),
    ("Toussaint, Pierre", ["MQ"], "A5", "Martiniquais surname"),
    ("Lamarre, Claude", ["GP"], "A5", "Guadeloupean surname"),
    ("de la Cruz, Miguel", ["CW"], "A5", "Spanish-origin Caribbean"),
    # ======================================================================
    # B1 - East Slavic (RU, UA, BY)
    # ======================================================================
    ("Ivanov, Sergei", ["RU"], "B1", "Most common Russian surname"),
    ("Petrov, Aleksandr", ["RU"], "B1", "Second most common Russian"),
    ("Smirnov, Andrei", ["RU"], "B1", "Third most common Russian"),
    ("Kuznetsov, Dmitri", ["RU"], "B1", "Fourth most common Russian"),
    ("Popov, Viktor", ["RU"], "B1", "Fifth most common Russian"),
    ("Sokolov, Mikhail", ["RU"], "B1", "Common Russian surname"),
    ("Lebedev, Pavel", ["RU"], "B1", "Russian surname"),
    ("Kozlov, Ivan", ["RU"], "B1", "Russian surname"),
    ("Novikov, Nikolai", ["RU"], "B1", "Russian surname"),
    ("Morozov, Boris", ["RU"], "B1", "Russian surname"),
    ("Shevchenko, Taras", ["UA"], "B1", "Common Ukrainian surname"),
    ("Kovalenko, Oleksiy", ["UA"], "B1", "Ukrainian surname"),
    ("Bondarenko, Iryna", ["UA"], "B1", "Ukrainian surname"),
    ("Lukashenko, Aliaksandr", ["BY"], "B1", "Belarusian surname"),
    ("Kolmogorov, Andrey", ["RU"], "B1", "Famous Russian mathematician"),
    ("Chebyshev, Pafnuty", ["RU"], "B1", "Russian mathematician"),
    ("Lobachevsky, Nikolai", ["RU"], "B1", "Russian mathematician"),
    ("Ivanova, Natalia", ["RU"], "B1", "Female Russian -ova suffix"),
    ("Petrova, Elena", ["RU"], "B1", "Female Russian -ova suffix"),
    ("Kuznetsova, Svetlana", ["RU"], "B1", "Female Russian -ova suffix"),
    # ======================================================================
    # B2 - West/South Slavic & Central Europe (PL, CZ, SK, HR, RS, SI,
    #       BG, RO, HU, BA, MK, AL, ME)
    # ======================================================================
    ("Novak, Jan", ["CZ"], "B2", "Most common Czech surname (ASCII)"),
    ("Svoboda, Karel", ["CZ"], "B2", "Common Czech surname"),
    ("Dvorak, Antonin", ["CZ"], "B2", "Czech composer surname (ASCII)"),
    ("Kowalski, Piotr", ["PL"], "B2", "Most common Polish surname"),
    ("Wisniewski, Andrzej", ["PL"], "B2", "Common Polish surname"),
    ("Lewandowski, Robert", ["PL"], "B2", "Polish footballer surname"),
    ("Horvat, Ivan", ["HR"], "B2", "Most common Croatian surname"),
    ("Jovanovic, Nikola", ["RS"], "B2", "Common Serbian surname"),
    ("Nikolic, Tomislav", ["RS"], "B2", "Serbian surname"),
    ("Popov, Georgi", ["BG"], "B2", "Common Bulgarian surname"),
    ("Nagy, Imre", ["HU"], "B2", "Most common Hungarian surname"),
    ("Toth, Istvan", ["HU"], "B2", "Common Hungarian surname"),
    ("Kovacs, Zoltan", ["HU"], "B2", "Common Hungarian surname"),
    ("Erdos, Pal", ["HU"], "B2", "Hungarian mathematician (ASCII)"),
    ("Ionescu, Mircea", ["RO"], "B2", "Most common Romanian surname"),
    ("Novaková, Jana", ["CZ"], "B2", "Female Czech -ova suffix"),
    ("Kowalska, Anna", ["PL"], "B2", "Female Polish -ska suffix"),
    ("Lewandowska, Klara", ["PL"], "B2", "Female Polish -ska suffix"),
    ("Petrović, Dragan", ["RS"], "B2", "Serbian with diacritic"),
    ("Marković, Ana", ["RS"], "B2", "Female Serbian surname"),
    # ======================================================================
    # B3 - Hellenic (GR, CY)
    # ======================================================================
    ("Papadopoulos, Nikos", ["GR"], "B3", "Most common Greek surname"),
    ("Nikolaou, Andreas", ["CY"], "B3", "Common Cypriot surname"),
    ("Georgiou, Stavros", ["GR"], "B3", "Common Greek surname"),
    ("Vasileiou, Kostas", ["GR"], "B3", "Greek surname"),
    ("Konstantinou, Maria", ["CY"], "B3", "Cypriot surname"),
    ("Christodoulou, Christos", ["CY"], "B3", "Common Cypriot surname"),
    ("Ioannou, Petros", ["CY"], "B3", "Cypriot surname"),
    ("Andreou, Sophia", ["CY"], "B3", "Female Cypriot surname"),
    ("Demetriou, Andreas", ["CY"], "B3", "Cypriot surname"),
    ("Karamanlis, Konstantinos", ["GR"], "B3", "Greek political surname"),
    ("Papandreou, Georgios", ["GR"], "B3", "Greek political surname"),
    ("Theodorakis, Mikis", ["GR"], "B3", "Greek composer surname"),
    ("Kazantzakis, Nikos", ["GR"], "B3", "Greek author surname"),
    ("Mavrogenis, Eleni", ["GR"], "B3", "Greek compound surname"),
    ("Alexopoulos, Dimitris", ["GR"], "B3", "Greek compound surname"),
    # ======================================================================
    # C1 - Greater Turkic (TR, AZ, TM, KG, KZ, UZ)
    # ======================================================================
    ("Yilmaz, Ahmet", ["TR"], "C1", "Most common Turkish surname"),
    ("Kaya, Mehmet", ["TR"], "C1", "Common Turkish surname"),
    ("Demir, Ali", ["TR"], "C1", "Common Turkish surname"),
    ("Celik, Fatma", ["TR"], "C1", "Common Turkish (ASCII)"),
    ("Sahin, Mustafa", ["TR"], "C1", "Common Turkish (ASCII)"),
    ("Aliyev, Ilham", ["AZ"], "C1", "Azerbaijani presidential surname"),
    ("Mammadov, Eldar", ["AZ"], "C1", "Most common Azerbaijani"),
    ("Hasanov, Rafik", ["AZ"], "C1", "Common Azerbaijani"),
    ("Berdimuhamedov, Gurbanguly", ["TM"], "C1", "Turkmen surname"),
    ("Erdogan, Recep", ["TR"], "C1", "Turkish political surname"),
    ("Karimov, Islam", ["UZ"], "C1", "Uzbek (territory maps to C1)"),
    ("Nazarbayev, Nursultan", ["KZ"], "C1", "Kazakh (territory maps to C1)"),
    ("Mirziyoyev, Shavkat", ["UZ"], "C1", "Uzbek surname"),
    ("Atambayev, Almazbek", ["KG"], "C1", "Kyrgyz surname"),
    ("Japarov, Sadyr", ["KG"], "C1", "Kyrgyz surname"),
    ("Tokayev, Kassym-Jomart", ["KZ"], "C1", "Kazakh compound given name"),
    ("Ozturk, Ayse", ["TR"], "C1", "Common Turkish surname"),
    ("Yildiz, Hasan", ["TR"], "C1", "Turkish surname"),
    ("Guliyev, Tural", ["AZ"], "C1", "Azerbaijani surname"),
    ("Niyazov, Saparmurat", ["TM"], "C1", "Turkmen surname"),
    # ======================================================================
    # C2 - Persian-Tajik (IR, AF, TJ)
    # ======================================================================
    ("Hosseini, Mohammad", ["IR"], "C2", "Common Iranian surname"),
    ("Rahimi, Ahmad", ["TJ"], "C2", "Tajik surname"),
    ("Mohammadi, Reza", ["IR"], "C2", "Common Iranian surname"),
    ("Ahmadi, Ali", ["IR"], "C2", "Common Iranian surname"),
    ("Karimi, Fatemeh", ["IR"], "C2", "Iranian female given name"),
    ("Hashemi, Akbar", ["IR"], "C2", "Iranian political surname"),
    ("Rezaei, Hossein", ["IR"], "C2", "Common Iranian surname"),
    ("Mousavi, Mir-Hossein", ["IR"], "C2", "Iranian hyphenated given"),
    ("Khayyam, Omar", ["IR"], "C2", "Historical Persian polymath"),
    ("Biruni, Abu Rayhan", ["AF"], "C2", "Historical Persian scholar"),
    ("Jafari, Saeed", ["IR"], "C2", "Iranian surname"),
    ("Ghorbani, Parisa", ["IR"], "C2", "Iranian female name"),
    ("Nazari, Davoud", ["IR"], "C2", "Iranian surname"),
    ("Moradi, Zahra", ["IR"], "C2", "Iranian female name"),
    ("Sharifi, Nader", ["TJ"], "C2", "Tajik surname"),
    # ======================================================================
    # C3 - Arabic Levant-Nile (IQ, SY, LB, JO, EG, SD, PS)
    # ======================================================================
    ("Al-Rashid, Omar", ["IQ"], "C3", "Iraqi Al- prefix surname"),
    ("Nasser, Gamal", ["EG"], "C3", "Egyptian political surname"),
    ("Ibrahim, Hassan", ["EG"], "C3", "Common Egyptian surname"),
    ("Hassan, Mahmoud", ["EG"], "C3", "Common Egyptian surname"),
    ("Ali, Mohamed", ["EG"], "C3", "Most common Arabic name"),
    ("Mohamed, Ahmed", ["EG"], "C3", "Very common Egyptian name"),
    ("Ahmed, Khaled", ["JO"], "C3", "Common Jordanian name"),
    ("Mahmoud, Sami", ["SY"], "C3", "Syrian surname"),
    ("Khalil, Gibran", ["LB"], "C3", "Lebanese surname"),
    ("Sabbagh, Hisham", ["SY"], "C3", "Levantine artisan surname"),
    ("Al-Khowarizmi, Muhammad", ["IQ"], "C3", "Historical mathematician"),
    ("El-Sisi, Abdel", ["EG"], "C3", "Egyptian El- prefix"),
    ("Darwish, Mahmoud", ["PS"], "C3", "Palestinian surname"),
    ("Hariri, Rafik", ["LB"], "C3", "Lebanese political surname"),
    ("Bakri, Saleh", ["PS"], "C3", "Palestinian surname"),
    ("Al-Majid, Tariq", ["IQ"], "C3", "Iraqi compound surname"),
    ("Hussein, Saddam", ["IQ"], "C3", "Iraqi name"),
    ("Mubarak, Hosni", ["EG"], "C3", "Egyptian political surname"),
    ("Jumblatt, Walid", ["LB"], "C3", "Lebanese Druze surname"),
    ("Bashir, Omar", ["SD"], "C3", "Sudanese surname"),
    # ======================================================================
    # C4 - Arabic Gulf (SA, AE, KW, QA, BH, OM, YE)
    # ======================================================================
    ("Al-Saud, Mohammed", ["SA"], "C4", "Saudi royal surname"),
    ("Al-Maktoum, Rashid", ["AE"], "C4", "Emirati royal surname"),
    ("Al-Thani, Tamim", ["QA"], "C4", "Qatari royal surname"),
    ("Al-Sabah, Jaber", ["KW"], "C4", "Kuwaiti royal surname"),
    ("Al-Khalifa, Hamad", ["BH"], "C4", "Bahraini royal surname"),
    ("Al-Said, Qaboos", ["OM"], "C4", "Omani royal surname"),
    ("Al-Nahyan, Zayed", ["AE"], "C4", "Emirati surname"),
    ("Al-Falasi, Ahmed", ["AE"], "C4", "Emirati tribal surname"),
    ("Al-Ghamdi, Saeed", ["SA"], "C4", "Saudi tribal surname"),
    ("Al-Otaibi, Fahad", ["SA"], "C4", "Saudi tribal surname"),
    ("Al-Rashidi, Nasser", ["KW"], "C4", "Kuwaiti tribal surname"),
    ("Al-Dosari, Khalid", ["QA"], "C4", "Qatari surname"),
    ("Al-Balushi, Said", ["OM"], "C4", "Omani surname"),
    ("Hadi, Abd Rabbuh", ["YE"], "C4", "Yemeni surname"),
    ("Al-Shamsi, Fatima", ["AE"], "C4", "Emirati female name"),
    # ======================================================================
    # C5 - Arabic Maghreb (MA, DZ, TN, LY, MR)
    # ======================================================================
    ("Bennani, Youssef", ["MA"], "C5", "Common Moroccan surname"),
    ("Boudiaf, Mohamed", ["DZ"], "C5", "Algerian political surname"),
    ("Benali, Zine", ["TN"], "C5", "Tunisian surname"),
    ("Trabelsi, Sami", ["TN"], "C5", "Common Tunisian surname"),
    ("Bouzid, Karim", ["DZ"], "C5", "Algerian surname"),
    ("Haftar, Khalifa", ["LY"], "C5", "Libyan political surname"),
    ("Essebsi, Beji", ["TN"], "C5", "Tunisian political surname"),
    ("Bouteflika, Abdelaziz", ["DZ"], "C5", "Algerian political surname"),
    ("Tebboune, Abdelmadjid", ["DZ"], "C5", "Algerian surname"),
    ("Cheddadi, Abdesselam", ["MA"], "C5", "Moroccan surname"),
    ("Gaddafi, Muammar", ["LY"], "C5", "Libyan political surname"),
    ("Belkacem, Najat", ["DZ"], "C5", "Algerian female name"),
    ("Ould Cheikh, Mohamed", ["MR"], "C5", "Mauritanian compound"),
    ("Benmoussa, Chakib", ["MA"], "C5", "Moroccan compound surname"),
    ("Zerhouni, Yazid", ["DZ"], "C5", "Algerian surname"),
    # ======================================================================
    # C6 - Hebrew Diaspora (IL)
    # ======================================================================
    ("Cohen, David", ["IL"], "C6", "Most common Israeli surname"),
    ("Levy, Sarah", ["IL"], "C6", "Second most common Israeli"),
    ("Mizrahi, Moshe", ["IL"], "C6", "Sephardic Israeli surname"),
    ("Ashkenazi, Gabi", ["IL"], "C6", "Ashkenazi-origin surname"),
    ("Shapiro, Avraham", ["IL"], "C6", "Eastern European Jewish"),
    ("Goldberg, Yoav", ["IL"], "C6", "German Jewish surname"),
    ("Friedman, Yitzhak", ["IL"], "C6", "Ashkenazi surname"),
    ("Rosenberg, Naftali", ["IL"], "C6", "German Jewish surname"),
    ("Bernstein, Uri", ["IL"], "C6", "Ashkenazi surname"),
    ("Weizmann, Chaim", ["IL"], "C6", "Historical Israeli surname"),
    ("Ben-Gurion, David", ["IL"], "C6", "Israeli hyphenated surname"),
    ("Netanyahu, Benjamin", ["IL"], "C6", "Israeli political surname"),
    ("Perelman, Grigory", ["IL"], "C6", "Russian Jewish in Israel"),
    ("Rabin, Yitzhak", ["IL"], "C6", "Israeli political surname"),
    ("Aumann, Robert", ["IL"], "C6", "Israeli Nobel laureate"),
    # ======================================================================
    # C7 - Armenian (AM)
    # ======================================================================
    ("Petrosyan, Tigran", ["AM"], "C7", "Common Armenian surname"),
    ("Sargsyan, Serzh", ["AM"], "C7", "Armenian political surname"),
    ("Harutyunyan, Gevorg", ["AM"], "C7", "Common Armenian surname"),
    ("Grigoryan, Armen", ["AM"], "C7", "Common Armenian surname"),
    ("Hovhannisyan, Levon", ["AM"], "C7", "Armenian surname"),
    ("Karapetyan, Karen", ["AM"], "C7", "Armenian surname"),
    ("Manukyan, Gagik", ["AM"], "C7", "Armenian surname"),
    ("Gasparyan, Sergey", ["AM"], "C7", "Armenian surname"),
    ("Khachaturian, Aram", ["AM"], "C7", "Armenian composer surname"),
    ("Darbinyan, Arshak", ["AM"], "C7", "Armenian surname"),
    ("Vardanyan, Ruben", ["AM"], "C7", "Armenian surname"),
    ("Minasyan, Hakob", ["AM"], "C7", "Armenian surname"),
    ("Mkrtchyan, Frunzik", ["AM"], "C7", "Armenian with consonant cluster"),
    ("Abrahamyan, Hovik", ["AM"], "C7", "Armenian surname"),
    ("Asatryan, Lilit", ["AM"], "C7", "Armenian female name"),
    # ======================================================================
    # C8 - Georgian (GE)
    # ======================================================================
    ("Beridze, Giorgi", ["GE"], "C8", "Common Georgian surname"),
    ("Tskhadadze, Kakhaber", ["GE"], "C8", "Georgian consonant cluster"),
    ("Shevardnadze, Eduard", ["GE"], "C8", "Georgian political surname"),
    ("Saakashvili, Mikheil", ["GE"], "C8", "Georgian political surname"),
    ("Ivanishvili, Bidzina", ["GE"], "C8", "Georgian -shvili suffix"),
    ("Jughashvili, Ioseb", ["GE"], "C8", "Georgian (Stalin's birth name)"),
    ("Meladze, Valery", ["GE"], "C8", "Georgian -dze suffix"),
    ("Kvaratskhelia, Khvicha", ["GE"], "C8", "Georgian complex surname"),
    ("Margvelashvili, Giorgi", ["GE"], "C8", "Georgian -shvili suffix"),
    ("Garibashvili, Irakli", ["GE"], "C8", "Georgian -shvili suffix"),
    ("Zhvania, Zurab", ["GE"], "C8", "Georgian surname"),
    ("Dolidze, Nino", ["GE"], "C8", "Georgian female name"),
    ("Kipiani, David", ["GE"], "C8", "Georgian surname"),
    ("Javakhishvili, Ivane", ["GE"], "C8", "Georgian -shvili"),
    ("Tsereteli, Zurab", ["GE"], "C8", "Georgian surname"),
    # ======================================================================
    # D1 - South Asia Indic (IN, NP, BT)
    # ======================================================================
    ("Sharma, Rajesh", ["IN"], "D1", "Most common North Indian surname"),
    ("Patel, Amit", ["IN"], "D1", "Common Gujarati surname"),
    ("Singh, Manmohan", ["IN"], "D1", "Common Sikh surname"),
    ("Kumar, Manoj", ["IN"], "D1", "Common Hindi-belt surname"),
    ("Gupta, Ashok", ["IN"], "D1", "Common North Indian surname"),
    ("Verma, Anita", ["IN"], "D1", "Common Hindi-belt surname"),
    ("Joshi, Murli", ["IN"], "D1", "Brahmin surname"),
    ("Mishra, Brajesh", ["IN"], "D1", "North Indian Brahmin surname"),
    ("Pandey, Deepak", ["IN"], "D1", "Common North Indian surname"),
    ("Mehta, Zubin", ["IN"], "D1", "Gujarati/Parsi surname"),
    ("Ramanujan, Srinivasa", ["IN"], "D1", "Famous Indian mathematician"),
    ("Chandrasekhar, Subrahmanyan", ["IN"], "D1", "Indian physicist"),
    ("Bose, Satyendra", ["IN"], "D1", "Bengali physicist in D1 context"),
    ("Raman, Chandrasekhara", ["IN"], "D1", "Indian Nobel physicist"),
    ("Tiwari, Neha", ["IN"], "D1", "North Indian female name"),
    ("Shrestha, Ram", ["NP"], "D1", "Common Nepali surname"),
    ("Adhikari, Sushil", ["NP"], "D1", "Nepali surname"),
    ("Dorji, Jigme", ["BT"], "D1", "Bhutanese surname"),
    ("Yadav, Lalu", ["IN"], "D1", "OBC North Indian surname"),
    ("Agarwal, Vinod", ["IN"], "D1", "Marwari surname"),
    # ======================================================================
    # D3 - Bengali (BD, and Bengali-speaking IN via BD CC)
    # ======================================================================
    ("Rahman, Mizanur", ["BD"], "D3", "Most common Bangladeshi surname"),
    ("Chowdhury, Anwar", ["BD"], "D3", "Common Bangladeshi surname"),
    ("Hossain, Kamal", ["BD"], "D3", "Common Bangladeshi surname"),
    ("Islam, Kazi Nazrul", ["BD"], "D3", "Common Bangladeshi surname"),
    ("Akter, Hasina", ["BD"], "D3", "Bangladeshi female name"),
    ("Begum, Khaleda", ["BD"], "D3", "Bangladeshi female honorific"),
    ("Tagore, Rabindranath", ["BD"], "D3", "Bengali Nobel laureate"),
    ("Bose, Jagadish", ["BD"], "D3", "Bengali physicist"),
    ("Sen, Amartya", ["BD"], "D3", "Bengali Nobel economist"),
    ("Chatterjee, Bankim", ["BD"], "D3", "Bengali Brahmin surname"),
    ("Mitra, Suchitra", ["BD"], "D3", "Bengali surname"),
    ("Sarkar, Prabir", ["BD"], "D3", "Bengali surname"),
    ("Ahmed, Fakhruddin", ["BD"], "D3", "Bangladeshi political surname"),
    ("Zaman, Munir", ["BD"], "D3", "Bangladeshi surname"),
    ("Huq, Shamsul", ["BD"], "D3", "Bangladeshi surname"),
    # ======================================================================
    # D4 - Pakistan-Urdu (PK)
    # ======================================================================
    ("Khan, Imran", ["PK"], "D4", "Most common Pakistani surname"),
    ("Malik, Asif", ["PK"], "D4", "Common Pakistani surname"),
    ("Hussain, Altaf", ["PK"], "D4", "Common Pakistani surname"),
    ("Shah, Nasir", ["PK"], "D4", "Common Pakistani surname"),
    ("Bhutto, Benazir", ["PK"], "D4", "Pakistani political surname"),
    ("Sharif, Nawaz", ["PK"], "D4", "Pakistani political surname"),
    ("Iqbal, Allama", ["PK"], "D4", "Pakistani philosopher surname"),
    ("Jinnah, Muhammad Ali", ["PK"], "D4", "Pakistani founder surname"),
    ("Salam, Abdus", ["PK"], "D4", "Pakistani Nobel physicist"),
    ("Ahmed, Mirza", ["PK"], "D4", "Pakistani surname"),
    ("Durrani, Ahmad Shah", ["PK"], "D4", "Pashtun surname"),
    ("Baloch, Liaquat", ["PK"], "D4", "Baloch ethnic surname"),
    ("Afridi, Shahid", ["PK"], "D4", "Pashtun tribal surname"),
    ("Qureshi, Shah Mahmood", ["PK"], "D4", "Pakistani surname"),
    ("Butt, Nazar", ["PK"], "D4", "Short Kashmiri-Punjabi surname"),
    # ======================================================================
    # D5 - Sinhala (LK)
    # ======================================================================
    ("Jayawardena, Mahela", ["LK"], "D5", "Common Sri Lankan surname"),
    ("Perera, Kumar", ["LK"], "D5", "Common Sinhalese surname"),
    ("Fernando, Tyrone", ["LK"], "D5", "Portuguese-origin Sri Lankan"),
    ("de Silva, Muttiah", ["LK"], "D5", "Portuguese particle Sri Lankan"),
    ("Wickramasinghe, Ranil", ["LK"], "D5", "Long Sinhalese surname"),
    ("Bandara, Sirimavo", ["LK"], "D5", "Sinhalese surname"),
    ("Rajapaksa, Mahinda", ["LK"], "D5", "Sri Lankan political surname"),
    ("Dissanayake, Anura", ["LK"], "D5", "Sinhalese surname"),
    ("Karunaratne, Dimuth", ["LK"], "D5", "Sinhalese surname"),
    ("Gunawardena, Philip", ["LK"], "D5", "Sinhalese surname"),
    ("Senanayake, Don Stephen", ["LK"], "D5", "Sinhalese compound"),
    ("Bandaranaike, Solomon", ["LK"], "D5", "Long Sinhalese surname"),
    ("Mendis, Dhananjaya", ["LK"], "D5", "Portuguese-origin Sri Lankan"),
    ("Samaraweera, Thilan", ["LK"], "D5", "Long Sinhalese surname"),
    ("Athulathmudali, Lalith", ["LK"], "D5", "Very long Sri Lankan"),
    # ======================================================================
    # E1 - Sinophone Mainland (CN)
    # ======================================================================
    ("Wang, Wei", ["CN"], "E1", "Most common Chinese surname"),
    ("Li, Na", ["CN"], "E1", "Second most common (short surname)"),
    ("Zhang, Yiming", ["CN"], "E1", "Third most common Chinese"),
    ("Liu, Cixin", ["CN"], "E1", "Common Chinese surname (author)"),
    ("Chen, Jingrun", ["CN"], "E1", "Common Chinese mathematician"),
    ("Yang, Chen-Ning", ["CN"], "E1", "Chinese Nobel physicist"),
    ("Huang, Kunyan", ["CN"], "E1", "Common Chinese surname"),
    ("Zhao, Ziyang", ["CN"], "E1", "Common Chinese surname"),
    ("Wu, Wenjun", ["CN"], "E1", "Chinese mathematician"),
    ("Zhou, Enlai", ["CN"], "E1", "Common Chinese surname"),
    ("Tao, Terence", ["CN"], "E1", "Chinese-Australian mathematician"),
    ("Yau, Shing-Tung", ["CN"], "E1", "Chinese Fields medalist"),
    ("Xu, Guoqi", ["CN"], "E1", "Short Chinese surname"),
    ("Sun, Tzu", ["CN"], "E1", "Historical Chinese surname"),
    ("Qian, Xuesen", ["CN"], "E1", "Chinese scientist"),
    ("Hua, Luogeng", ["CN"], "E1", "Chinese mathematician"),
    ("Shi, Yigong", ["CN"], "E1", "Short Chinese surname"),
    ("He, Jiankui", ["CN"], "E1", "Short Chinese surname"),
    ("Ma, Yun", ["CN"], "E1", "Short Chinese surname"),
    ("Gu, Chaohao", ["CN"], "E1", "Short Chinese surname"),
    # ======================================================================
    # E2 - Sinophone Traditional (TW, HK, MO)
    # ======================================================================
    ("Chen, Mei-Ling", ["TW"], "E2", "Common Taiwanese surname"),
    ("Lin, Yu-tang", ["TW"], "E2", "Common Taiwanese surname"),
    ("Huang, Chun-Ming", ["TW"], "E2", "Common Taiwanese surname"),
    ("Wong, Ka-Fai", ["HK"], "E2", "Cantonese romanisation"),
    ("Lam, Carrie", ["HK"], "E2", "Cantonese surname"),
    ("Chan, Jackie", ["HK"], "E2", "Cantonese surname"),
    ("Tsai, Ing-wen", ["TW"], "E2", "Taiwanese political surname"),
    ("Wu, Bai", ["TW"], "E2", "Common Taiwanese surname"),
    ("Chiang, Kai-shek", ["TW"], "E2", "Historical Taiwanese surname"),
    ("Ho, Edmund", ["MO"], "E2", "Macanese surname"),
    ("Leung, Chun-ying", ["HK"], "E2", "Cantonese surname"),
    ("Cheung, Maggie", ["HK"], "E2", "Cantonese surname"),
    ("Lai, Jimmy", ["HK"], "E2", "Cantonese surname"),
    ("Yip, Man", ["HK"], "E2", "Short Cantonese surname"),
    ("Ng, Yat-siu", ["HK"], "E2", "Very short Cantonese surname"),
    # ======================================================================
    # E3 - Japanese (JP)
    # ======================================================================
    ("Tanaka, Hiroshi", ["JP"], "E3", "Common Japanese surname"),
    ("Suzuki, Yuko", ["JP"], "E3", "Second most common Japanese"),
    ("Takahashi, Akira", ["JP"], "E3", "Common Japanese surname"),
    ("Watanabe, Ken", ["JP"], "E3", "Common Japanese surname"),
    ("Ito, Kiyoshi", ["JP"], "E3", "Japanese mathematician (ASCII)"),
    ("Yamamoto, Isoroku", ["JP"], "E3", "Common Japanese surname"),
    ("Nakamura, Shuji", ["JP"], "E3", "Japanese Nobel physicist"),
    ("Kobayashi, Makoto", ["JP"], "E3", "Japanese Nobel physicist"),
    ("Kato, Tosio", ["JP"], "E3", "Japanese mathematician (ASCII)"),
    ("Yoshida, Kosaku", ["JP"], "E3", "Japanese mathematician"),
    ("Mori, Shigefumi", ["JP"], "E3", "Japanese Fields medalist"),
    ("Hironaka, Heisuke", ["JP"], "E3", "Japanese Fields medalist"),
    ("Kodaira, Kunihiko", ["JP"], "E3", "Japanese Fields medalist"),
    ("Sato, Mikio", ["JP"], "E3", "Common Japanese surname"),
    ("Saito, Morihiko", ["JP"], "E3", "Common Japanese surname"),
    ("Ogawa, Yoko", ["JP"], "E3", "Japanese female author"),
    ("Abe, Shinzo", ["JP"], "E3", "Short Japanese surname"),
    ("Ono, Yoko", ["JP"], "E3", "Short Japanese surname"),
    ("Doi, Takako", ["JP"], "E3", "Short Japanese surname"),
    ("Ku, Michio", ["JP"], "E3", "Very short Japanese surname"),
    # ======================================================================
    # E4 - Korean (KR, KP)
    # ======================================================================
    ("Kim, Minhyong", ["KR"], "E4", "Most common Korean surname"),
    ("Lee, Sangwon", ["KR"], "E4", "Second most common Korean"),
    ("Park, Jiyeon", ["KR"], "E4", "Third most common Korean"),
    ("Choi, Youngin", ["KR"], "E4", "Common Korean surname"),
    ("Jung, Haeun", ["KR"], "E4", "Common Korean surname"),
    ("Kang, Daniel", ["KR"], "E4", "Common Korean surname"),
    ("Cho, Yong-Pil", ["KR"], "E4", "Common Korean surname"),
    ("Yoon, Seok-yeol", ["KR"], "E4", "Korean political surname"),
    ("Jang, Yeong-sil", ["KR"], "E4", "Korean inventor surname"),
    ("Lim, Yoona", ["KR"], "E4", "Common Korean surname"),
    ("Shin, Kyung-sook", ["KR"], "E4", "Korean author surname"),
    ("Han, Kang", ["KR"], "E4", "Korean Nobel laureate"),
    ("Oh, Yeon-seo", ["KR"], "E4", "Common Korean surname"),
    ("Seo, Taiji", ["KR"], "E4", "Common Korean surname"),
    ("Hwang, Woo-suk", ["KR"], "E4", "Korean scientist surname"),
    ("Ri, Yong-ho", ["KP"], "E4", "North Korean surname"),
    ("Ko, Un", ["KR"], "E4", "Very short Korean surname"),
    ("Ryu, Hyun-jin", ["KR"], "E4", "Korean baseball player"),
    ("Bae, Doona", ["KR"], "E4", "Short Korean surname"),
    ("Moon, Jae-in", ["KR"], "E4", "Korean political surname"),
    # ======================================================================
    # E5 - Vietnamese (VN)
    # ======================================================================
    ("Nguyen, Van Anh", ["VN"], "E5", "Most common Vietnamese surname"),
    ("Tran, Minh", ["VN"], "E5", "Second most common Vietnamese"),
    ("Le, Duan", ["VN"], "E5", "Short Vietnamese surname"),
    ("Pham, Van Dong", ["VN"], "E5", "Common Vietnamese surname"),
    ("Hoang, Xuan Han", ["VN"], "E5", "Vietnamese mathematician"),
    ("Vu, Ha Van", ["VN"], "E5", "Vietnamese mathematician"),
    ("Vo, Nguyen Giap", ["VN"], "E5", "Vietnamese military leader"),
    ("Dang, Thai Son", ["VN"], "E5", "Vietnamese pianist surname"),
    ("Bui, Quang Khiem", ["VN"], "E5", "Common Vietnamese surname"),
    ("Do, Muoi", ["VN"], "E5", "Short Vietnamese surname"),
    ("Ngo, Bao Chau", ["VN"], "E5", "Vietnamese Fields medalist"),
    ("Duong, Thu Huong", ["VN"], "E5", "Vietnamese author"),
    ("Truong, Chinh", ["VN"], "E5", "Vietnamese political name"),
    ("Dao, Trong Thi", ["VN"], "E5", "Vietnamese mathematician"),
    ("Dinh, Tien Cuong", ["VN"], "E5", "Vietnamese mathematician"),
    ("Ha, Huy Khoai", ["VN"], "E5", "Vietnamese mathematician"),
    ("Ly, Thai To", ["VN"], "E5", "Short Vietnamese surname"),
    ("To, Tat Dat", ["VN"], "E5", "Short Vietnamese surname"),
    ("Ho, Chi Minh", ["VN"], "E5", "Vietnamese historical name"),
    ("Ta, Quang Buu", ["VN"], "E5", "Short Vietnamese surname"),
    # ======================================================================
    # E6 - Mainland SEA (TH, KH, LA, MM)
    # Note: MM (Myanmar) is NOT in the territory map, so we skip it
    # ======================================================================
    ("Srisai, Pornthip", ["TH"], "E6", "Thai surname"),
    ("Channarong, Somchai", ["TH"], "E6", "Thai surname"),
    ("Sompong, Prayut", ["TH"], "E6", "Thai surname"),
    ("Phetsavong, Khamla", ["LA"], "E6", "Lao surname"),
    ("Vongsa, Bouasone", ["LA"], "E6", "Lao surname"),
    ("Sokha, Kem", ["KH"], "E6", "Khmer surname"),
    ("Chidchob, Newin", ["TH"], "E6", "Thai surname"),
    ("Shinawatra, Thaksin", ["TH"], "E6", "Thai political surname"),
    ("Phibunsongkhram, Plaek", ["TH"], "E6", "Long Thai surname"),
    ("Sayasone, Choummaly", ["LA"], "E6", "Lao political surname"),
    ("Siphandone, Khamtay", ["LA"], "E6", "Lao surname"),
    ("Hun, Sen", ["KH"], "E6", "Short Khmer surname"),
    ("Rainsy, Sam", ["KH"], "E6", "Khmer political surname"),
    ("Norodom, Sihamoni", ["KH"], "E6", "Khmer royal surname"),
    ("Intharath, Prasert", ["TH"], "E6", "Thai surname"),
    # ======================================================================
    # E7 - Maritime SEA (SG, MY, ID, PH, BN)
    # ======================================================================
    ("Tan, Wei Ming", ["SG"], "E7", "Common Singaporean surname"),
    ("Lim, Goh Tong", ["MY"], "E7", "Malaysian Chinese surname"),
    ("Wong, Ah Fook", ["MY"], "E7", "Malaysian Chinese surname"),
    ("Sukarno, Achmed", ["ID"], "E7", "Indonesian mononymic"),
    ("Widodo, Joko", ["ID"], "E7", "Javanese Indonesian surname"),
    ("Rizal, Jose", ["PH"], "E7", "Filipino national hero"),
    ("Santos, Benigno", ["PH"], "E7", "Filipino Spanish surname"),
    ("Aquino, Corazon", ["PH"], "E7", "Filipino political surname"),
    ("Abdullah, Ahmad Badawi", ["MY"], "E7", "Malay patronymic"),
    ("Mahathir, Mohamad", ["MY"], "E7", "Malay surname"),
    ("Bolkiah, Hassanal", ["BN"], "E7", "Bruneian royal surname"),
    ("Marcos, Ferdinand", ["PH"], "E7", "Filipino political surname"),
    ("Habibie, Bacharuddin", ["ID"], "E7", "Indonesian surname"),
    ("Wahid, Abdurrahman", ["ID"], "E7", "Indonesian surname"),
    ("Megawati, Sukarnoputri", ["ID"], "E7", "Indonesian compound"),
    ("Goh, Chok Tong", ["SG"], "E7", "Singaporean Chinese surname"),
    ("Lee, Kuan Yew", ["SG"], "E7", "Singaporean surname"),
    ("Duterte, Rodrigo", ["PH"], "E7", "Filipino surname"),
    ("Suharto, Raden", ["ID"], "E7", "Javanese mononymic"),
    ("Yusof, Ishak", ["SG"], "E7", "Malay Singaporean"),
    # ======================================================================
    # F1 - SSA Francophone (SN, CI, CM, CD, MG, BF, ML, etc.)
    # ======================================================================
    ("Diallo, Mamadou", ["SN"], "F1", "Common Senegalese surname"),
    ("Traore, Ousmane", ["CI"], "F1", "Common Ivorian surname (ASCII)"),
    ("Coulibaly, Ibrahim", ["CI"], "F1", "Common Ivorian surname"),
    ("Ndiaye, Issa", ["SN"], "F1", "Common Senegalese surname"),
    ("Ouattara, Alassane", ["CI"], "F1", "Ivorian political surname"),
    ("Compaore, Blaise", ["BF"], "F1", "Burkinabe surname (ASCII)"),
    ("Ravalomanana, Marc", ["MG"], "F1", "Malagasy surname"),
    ("Biya, Paul", ["CM"], "F1", "Cameroonian political surname"),
    ("Toure, Amadou", ["ML"], "F1", "Malian surname"),
    ("Keita, Ibrahim", ["ML"], "F1", "Malian surname"),
    ("Senghor, Leopold", ["SN"], "F1", "Senegalese poet-president"),
    ("Mbeki, Moussa", ["SN"], "F1", "Senegalese surname"),
    ("Kone, Arouna", ["CI"], "F1", "Ivorian surname"),
    ("Ouedraogo, Gerard", ["BF"], "F1", "Burkinabe surname"),
    ("Ratsiraka, Didier", ["MG"], "F1", "Malagasy surname"),
    # ======================================================================
    # F2 - SSA Anglophone (NG, GH, KE, TZ, UG, ZW, ZM, etc.)
    # ======================================================================
    ("Okafor, Chukwu", ["NG"], "F2", "Common Nigerian Igbo surname"),
    ("Mwangi, James", ["KE"], "F2", "Common Kenyan surname"),
    ("Adeyemi, Ade", ["NG"], "F2", "Yoruba Nigerian surname"),
    ("Osei, Kofi", ["GH"], "F2", "Common Ghanaian surname"),
    ("Mensah, Kwame", ["GH"], "F2", "Common Ghanaian surname"),
    ("Kamau, John", ["KE"], "F2", "Kikuyu Kenyan surname"),
    ("Mugabe, Robert", ["ZW"], "F2", "Zimbabwean political surname"),
    ("Mandela, Nelson", ["ZW"], "F2", "SA surname in ZW CC context"),
    ("Nyerere, Julius", ["TZ"], "F2", "Tanzanian political surname"),
    ("Museveni, Yoweri", ["UG"], "F2", "Ugandan political surname"),
    ("Achebe, Chinua", ["NG"], "F2", "Nigerian Igbo author"),
    ("Soyinka, Wole", ["NG"], "F2", "Nigerian Nobel laureate"),
    ("Kenyatta, Uhuru", ["KE"], "F2", "Kenyan political surname"),
    ("Odinga, Raila", ["KE"], "F2", "Kenyan political surname"),
    ("Banda, Hastings", ["MW"], "F2", "Malawian surname"),
    ("Kaunda, Kenneth", ["ZM"], "F2", "Zambian political surname"),
    ("Okonkwo, Emeka", ["NG"], "F2", "Nigerian Igbo surname"),
    ("Agyeman, Nana", ["GH"], "F2", "Ghanaian Akan surname"),
    ("Wainaina, Binyavanga", ["KE"], "F2", "Kenyan author surname"),
    ("Nkrumah, Kwame", ["GH"], "F2", "Ghanaian political surname"),
    # ======================================================================
    # F3 - Horn of Africa (ET, ER)
    # ======================================================================
    ("Haile, Gebrselassie", ["ET"], "F3", "Ethiopian runner surname"),
    ("Abiy, Ahmed", ["ET"], "F3", "Ethiopian political name"),
    ("Isaias, Afwerki", ["ER"], "F3", "Eritrean political surname"),
    ("Meles, Zenawi", ["ET"], "F3", "Ethiopian political name"),
    ("Tedros, Adhanom", ["ET"], "F3", "Ethiopian WHO director"),
    ("Bekele, Kenenisa", ["ET"], "F3", "Ethiopian runner surname"),
    ("Gebre, Derartu", ["ET"], "F3", "Ethiopian runner surname"),
    ("Assefa, Tigist", ["ET"], "F3", "Ethiopian female name"),
    ("Mesfin, Wolde", ["ET"], "F3", "Ethiopian surname"),
    ("Teshome, Mulatu", ["ET"], "F3", "Ethiopian political surname"),
    ("Habtemariam, Ghideon", ["ER"], "F3", "Eritrean surname"),
    ("Tesfagiorgis, Mussie", ["ER"], "F3", "Eritrean long surname"),
    ("Kidane, Biniam", ["ER"], "F3", "Eritrean cyclist surname"),
    ("Amanuel, Solomon", ["ER"], "F3", "Eritrean surname"),
    ("Desta, Almaz", ["ET"], "F3", "Ethiopian female name"),
    # ======================================================================
    # F4 - Lusophone Africa (MZ, AO, CV, GW, ST)
    # ======================================================================
    ("Silva, Joao", ["MZ"], "F4", "Common Lusophone surname"),
    ("Santos, Ana", ["AO"], "F4", "Common Angolan surname"),
    ("Ferreira, Manuel", ["MZ"], "F4", "Portuguese-origin surname"),
    ("Pereira, Aristides", ["CV"], "F4", "Cape Verdean surname"),
    ("Neto, Agostinho", ["AO"], "F4", "Angolan political surname"),
    ("Machel, Samora", ["MZ"], "F4", "Mozambican political surname"),
    ("dos Santos, Jose", ["AO"], "F4", "Angolan compound surname"),
    ("Lourenco, Joao", ["AO"], "F4", "Angolan political surname"),
    ("Guebuza, Armando", ["MZ"], "F4", "Mozambican political surname"),
    ("Vieira, Joao", ["GW"], "F4", "Guinea-Bissau surname"),
    ("Costa, Maria", ["CV"], "F4", "Cape Verdean surname"),
    ("Lopes, Carlos", ["CV"], "F4", "Cape Verdean surname"),
    ("Monteiro, Antonio", ["CV"], "F4", "Cape Verdean surname"),
    ("Pires, Pedro", ["CV"], "F4", "Cape Verdean surname"),
    ("Chissano, Joaquim", ["MZ"], "F4", "Mozambican political surname"),
    # ======================================================================
    # G1 - Latin America (MX, BR, AR, CO, CL, PE, VE, etc.)
    # ======================================================================
    ("Garcia, Carlos", ["MX"], "G1", "Most common Mexican surname"),
    ("Rodriguez, Maria", ["MX"], "G1", "Common Mexican surname"),
    ("Hernandez, Juan", ["MX"], "G1", "Common Mexican surname"),
    ("Lopez, Andres Manuel", ["MX"], "G1", "Mexican political name"),
    ("Martinez, Jose", ["MX"], "G1", "Common Mexican surname"),
    ("Gonzalez, Felipe", ["MX"], "G1", "Common Mexican surname"),
    ("Silva, Ana Paula", ["BR"], "G1", "Common Brazilian surname"),
    ("Oliveira, Joao", ["BR"], "G1", "Common Brazilian surname"),
    ("Souza, Marcos", ["BR"], "G1", "Common Brazilian surname"),
    ("Ferreira, Dilma", ["BR"], "G1", "Brazilian surname"),
    ("Fernandez, Cristina", ["AR"], "G1", "Argentine surname"),
    ("Borges, Jorge Luis", ["AR"], "G1", "Argentine author surname"),
    ("Uribe, Alvaro", ["CO"], "G1", "Colombian political surname"),
    ("Neruda, Pablo", ["CL"], "G1", "Chilean Nobel laureate"),
    ("Vargas Llosa, Mario", ["PE"], "G1", "Peruvian compound surname"),
    ("Chavez, Hugo", ["VE"], "G1", "Venezuelan political surname"),
    ("Garcia Marquez, Gabriel", ["CO"], "G1", "Colombian compound surname"),
    ("Lula, da Silva", ["BR"], "G1", "Brazilian compound surname"),
    ("Peron, Juan", ["AR"], "G1", "Argentine political surname"),
    ("Allende, Salvador", ["CL"], "G1", "Chilean political surname"),
    # ======================================================================
    # Historical names map to their actual country code's region
    # (H1 is not a territory-mapped region; historical names use their
    #  country of origin's CC)
    # ======================================================================
    ("Newton, Isaac", ["GB"], "A1", "British historical — maps to A1"),
    ("Leibniz, Gottfried", ["DE"], "A2", "German historical — maps to A2"),
    ("Descartes, Rene", ["FR"], "A2", "French historical — maps to A2"),
    ("Pascal, Blaise", ["FR"], "A2", "French historical — maps to A2"),
    ("Fermat, Pierre", ["FR"], "A2", "French historical — maps to A2"),
    ("Euler, Leonhard", ["CH"], "A2", "Swiss historical — maps to A2"),
    ("Gauss, Carl Friedrich", ["DE"], "A2", "German historical — maps to A2"),
    ("Archimedes, Syracuse", ["GR"], "B3", "Greek historical — maps to B3"),
    # ======================================================================
    # Residual and quarantine entries
    # ======================================================================
    # R0/Z0 are not in IMPLEMENTED_REGIONS, so unknown CCs fall through
    # to pattern matching. We test with actual valid CCs instead.
]


# Total count sanity check
assert (
    len(REGION_TEST_CASES) >= 550
), f"Expected >= 550 test cases, got {len(REGION_TEST_CASES)}"


# ---------------------------------------------------------------------------
# Region coverage verification data
# ---------------------------------------------------------------------------

ALL_37_REGIONS = {
    "A1",
    "A2",
    "A3",
    "A4",
    "A5",
    "B1",
    "B2",
    "B3",
    "C1",
    "C2",
    "C3",
    "C4",
    "C5",
    "C6",
    "C7",
    "C8",
    "D1",
    "D3",
    "D4",
    "D5",
    "E1",
    "E2",
    "E3",
    "E4",
    "E5",
    "E6",
    "E7",
    "F1",
    "F2",
    "F3",
    "F4",
    "G1",
}
# Note: C9, D2, H1, R0, Z0 are virtual/overlay regions without their own
# territory codes. C9 territories (KG, KZ, UZ) map to C1. D2 is sub-regional
# within IN (→D1). H1, R0, Z0 have no territory mapping.

REGIONS_WITH_TERRITORY_CODES = ALL_37_REGIONS - {"C9", "D2", "H1", "R0", "Z0"}


# ---------------------------------------------------------------------------
# Diaspora / ambiguous names — same surname, different country codes
# ---------------------------------------------------------------------------

DIASPORA_CASES = [
    # NOTE: Each name string must be UNIQUE across all test lists because
    # RegionManager caches by CanonicalLatin (ignoring CountryCodes).
    # Use distinct given names to avoid cache collisions.
    #
    # "Lee" resolves differently depending on CC
    ("Lee, Patricia", ["US"], "A1", "Lee as Anglo surname"),
    ("Lee, Hyunwoo", ["KR"], "E4", "Lee as Korean surname"),
    ("Lee, Hsien Loong", ["SG"], "E7", "Lee as Singaporean surname"),
    ("Lee, Siu-lung", ["HK"], "E2", "Lee as Hong Kong surname"),
    # "Kim" — Korean vs other
    ("Kim, Yuna", ["KR"], "E4", "Kim as Korean surname"),
    ("Kim, Russell", ["US"], "A1", "Kim as US surname"),
    # "Singh" — Indian vs diaspora
    ("Singh, Atal Bihari", ["IN"], "D1", "Singh as Indian surname"),
    ("Singh, Jagmeet", ["CA"], "A1", "Singh as Canadian Sikh"),
    # "Chen" — mainland vs Taiwan vs Singapore
    ("Chen, Guoqiang", ["CN"], "E1", "Chen as mainland Chinese"),
    ("Chen, Shu-bian", ["TW"], "E2", "Chen as Taiwanese"),
    ("Chen, Ah Kow", ["SG"], "E7", "Chen as Singaporean"),
    # "Ali" — Arabic vs Pakistani vs other
    ("Ali, Hosam", ["EG"], "C3", "Ali as Egyptian"),
    ("Ali, Choudhury", ["PK"], "D4", "Ali as Pakistani"),
    ("Ali, Ayaan Hirsi", ["NL"], "A2", "Ali as Dutch Somali"),
    # "Wang" — mainland vs Taiwan
    ("Wang, Daqing", ["CN"], "E1", "Wang as mainland Chinese"),
    ("Wang, Ting-Yu", ["TW"], "E2", "Wang as Taiwanese"),
    # "Martin" — Anglo vs French vs Spanish
    ("Martin, Dean", ["US"], "A1", "Martin as Anglo surname"),
    ("Martin, Francois", ["FR"], "A2", "Martin as French surname"),
    ("Martin, Luis Alberto", ["MX"], "G1", "Martin as Mexican surname"),
    # "Silva" — Portuguese vs Brazilian vs African
    ("Silva, Manuel", ["PT"], "A2", "Silva as Portuguese"),
    ("Silva, Marcos", ["BR"], "G1", "Silva as Brazilian"),
    ("Silva, Alberto", ["MZ"], "F4", "Silva as Mozambican"),
    # "Nguyen" — Vietnamese diaspora
    ("Nguyen, Thanh Lam", ["VN"], "E5", "Nguyen in Vietnam"),
    ("Nguyen, Viet Thanh", ["US"], "A1", "Nguyen in US diaspora"),
    # "Park" — Korean vs other
    ("Park, Jimin", ["KR"], "E4", "Park as Korean"),
    ("Park, Robert", ["US"], "A1", "Park as Anglo surname"),
    # "Garcia" — Spanish vs Latin American
    ("Garcia, Antonio", ["ES"], "A2", "Garcia as Spanish"),
    ("Garcia, Enrique", ["MX"], "G1", "Garcia as Mexican"),
    # "Kumar" — Indian vs diaspora
    ("Kumar, Rajesh", ["IN"], "D1", "Kumar in India"),
    ("Kumar, Vijay", ["US"], "A1", "Kumar in US diaspora"),
]


# ---------------------------------------------------------------------------
# Female name variants with gendered suffixes
# ---------------------------------------------------------------------------

FEMALE_VARIANT_CASES = [
    # Russian female -ova / -aya
    ("Ivanova, Natalia", ["RU"], "B1", "Russian female -ova"),
    ("Petrova, Elena", ["RU"], "B1", "Russian female -ova"),
    ("Kuznetsova, Svetlana", ["RU"], "B1", "Russian female -ova"),
    ("Zakharova, Maria", ["RU"], "B1", "Russian female -ova"),
    ("Kovalevskaya, Sofia", ["RU"], "B1", "Russian female -aya"),
    # Czech female -ova
    ("Novakova, Jana", ["CZ"], "B2", "Czech female -ova (ASCII)"),
    ("Svobodova, Lenka", ["CZ"], "B2", "Czech female -ova (ASCII)"),
    ("Dvorakova, Petra", ["CZ"], "B2", "Czech female -ova (ASCII)"),
    # Polish female -ska
    ("Kowalska, Anna", ["PL"], "B2", "Polish female -ska"),
    ("Lewandowska, Klara", ["PL"], "B2", "Polish female -ska"),
    ("Wisniowska, Maria", ["PL"], "B2", "Polish female variant"),
    # Bulgarian female -ova
    ("Popova, Ivanka", ["BG"], "B2", "Bulgarian female -ova"),
    ("Georgieva, Kristalina", ["BG"], "B2", "Bulgarian female -eva"),
    # Ukrainian female -enko / -ko
    ("Bondarenko, Iryna", ["UA"], "B1", "Ukrainian female -enko"),
    ("Tymoshenko, Yulia", ["UA"], "B1", "Ukrainian female political"),
]


# ---------------------------------------------------------------------------
# Compound / hyphenated / particle names
# ---------------------------------------------------------------------------

COMPOUND_NAME_CASES = [
    # Anglo compound
    ("O'Brien, Conan", ["IE"], "A1", "Irish O' prefix"),
    ("O'Sullivan, Sonia", ["IE"], "A1", "Irish O' prefix"),
    ("MacDonald, John", ["CA"], "A1", "Scottish Mac prefix"),
    ("McGregor, Ewan", ["GB"], "A1", "Scottish Mc prefix"),
    # Dutch particles
    ("van den Berg, Pieter", ["NL"], "A2", "Dutch double particle"),
    ("van der Waerden, Bartel", ["NL"], "A2", "Dutch van der"),
    ("de Vries, Hugo", ["NL"], "A2", "Dutch de"),
    # French particles
    ("de Beauvoir, Simone", ["FR"], "A2", "French particle"),
    ("du Chatelet, Emilie", ["FR"], "A2", "French du"),
    # Spanish compound
    ("Garcia Lopez, Antonio", ["ES"], "A2", "Spanish double surname"),
    ("Garcia Marquez, Gabriel", ["CO"], "G1", "Colombian double surname"),
    ("Vargas Llosa, Mario", ["PE"], "G1", "Peruvian double surname"),
    # Portuguese compound
    ("da Silva, Antonio", ["PT"], "A2", "Portuguese da"),
    ("dos Santos, Jose", ["AO"], "F4", "Angolan Portuguese compound"),
    # Hebrew compound
    ("Ben-Gurion, David", ["IL"], "C6", "Hebrew Ben- prefix"),
    # Arabic compound
    ("Al-Rashid, Omar", ["IQ"], "C3", "Arabic Al- prefix"),
    ("El-Sisi, Abdel", ["EG"], "C3", "Arabic El- prefix"),
    ("Al-Saud, Mohammed", ["SA"], "C4", "Arabic Al- prefix"),
    # Sri Lankan compound
    ("de Silva, Muttiah", ["LK"], "D5", "Portuguese-Sinhalese compound"),
    # Kazakh hyphenated given
    ("Tokayev, Kassym-Jomart", ["KZ"], "C1", "Kazakh hyphenated given"),
    # Korean hyphenated given
    ("Hwang, Woo-suk", ["KR"], "E4", "Korean hyphenated given"),
    ("Moon, Jae-in", ["KR"], "E4", "Korean hyphenated given"),
]


# ---------------------------------------------------------------------------
# Short names (2-3 character surnames)
# ---------------------------------------------------------------------------

SHORT_NAME_CASES = [
    ("Li, Na", ["CN"], "E1", "2-char Chinese surname"),
    ("Wu, Wenjun", ["CN"], "E1", "2-char Chinese surname"),
    ("Xu, Guoqi", ["CN"], "E1", "2-char Chinese surname"),
    ("Ma, Yun", ["CN"], "E1", "2-char Chinese surname"),
    ("He, Jiankui", ["CN"], "E1", "2-char Chinese surname"),
    ("Gu, Chaohao", ["CN"], "E1", "2-char Chinese surname"),
    ("Ng, Andrew", ["US"], "A1", "2-char Cantonese in US"),
    ("Ng, Yat-siu", ["HK"], "E2", "2-char Cantonese in HK"),
    ("Ko, Un", ["KR"], "E4", "2-char Korean surname"),
    ("Le, Duan", ["VN"], "E5", "2-char Vietnamese surname"),
    ("Do, Muoi", ["VN"], "E5", "2-char Vietnamese surname"),
    ("Ho, Chi Minh", ["VN"], "E5", "2-char Vietnamese surname"),
    ("Ho, Edmund", ["MO"], "E2", "2-char surname in Macau"),
    ("Abe, Shinzo", ["JP"], "E3", "3-char Japanese surname"),
    ("Ono, Yoko", ["JP"], "E3", "3-char Japanese surname"),
    ("Doi, Takako", ["JP"], "E3", "3-char Japanese surname"),
    ("Bae, Doona", ["KR"], "E4", "3-char Korean surname"),
    ("Oh, Yeon-seo", ["KR"], "E4", "2-char Korean surname"),
    ("Ha, Huy Khoai", ["VN"], "E5", "2-char Vietnamese surname"),
    ("To, Tat Dat", ["VN"], "E5", "2-char Vietnamese surname"),
]


# ---------------------------------------------------------------------------
# Diacritics preservation
# ---------------------------------------------------------------------------

DIACRITICS_CASES = [
    ("Muller, Hans", ["DE"], "A2", "German u-umlaut (ASCII input)"),
    ("Erdos, Pal", ["HU"], "B2", "Hungarian o-double-acute (ASCII)"),
    ("Dvorak, Antonin", ["CZ"], "B2", "Czech r-hacek (ASCII)"),
    ("Poincare, Henri", ["FR"], "A2", "French e-acute (ASCII)"),
    ("Noether, Emmy", ["DE"], "A2", "German oe digraph"),
    ("Sjoberg, Anders", ["SE"], "A3", "Swedish o-umlaut (ASCII)"),
    ("Jonsson, Bjarni", ["IS"], "A3", "Icelandic o-acute (ASCII)"),
    ("Celik, Fatma", ["TR"], "C1", "Turkish c-cedilla (ASCII)"),
    ("Sahin, Mustafa", ["TR"], "C1", "Turkish s-cedilla (ASCII)"),
    ("Yilmaz, Ahmet", ["TR"], "C1", "Turkish i-dotless (ASCII)"),
    ("Petrović, Dragan", ["RS"], "B2", "Serbian c-acute"),
    ("Marković, Ana", ["RS"], "B2", "Serbian c-acute"),
    ("Nguyen, Van Anh", ["VN"], "E5", "Vietnamese unmarked (ASCII)"),
    ("Berzins, Janis", ["LV"], "A3", "Latvian cedilla (ASCII)"),
    ("Kalninsh, Arvids", ["LV"], "A3", "Latvian (ASCII)"),
]


# ---------------------------------------------------------------------------
# Detection without country codes (pure pattern/ML/script-based)
# ---------------------------------------------------------------------------

NO_CC_CASES = [
    ("Smith, John", "A1", "Clearly Anglo surname"),
    ("Johnson, Emily", "A1", "Clearly Anglo surname"),
    ("Muller, Hans", "A2", "German surname"),
    ("Rossi, Paolo", "A2", "Italian surname"),
    ("Johansson, Sven", "A3", "Swedish -sson suffix"),
    ("Ivanov, Sergei", "B1", "Russian -ov suffix"),
    ("Papadopoulos, Nikos", "B3", "Greek -opoulos suffix"),
    ("Tanaka, Hiroshi", "E3", "Japanese surname"),
    ("Suzuki, Yuko", "E3", "Japanese surname"),
    ("Kim, Minhyong", "E4", "Korean surname"),
    ("Park, Jiyeon", "E4", "Korean surname"),
    ("Nguyen, Van Anh", "E5", "Vietnamese Nguyen"),
    ("Kowalski, Piotr", "B2", "Polish surname"),
    ("Garcia, Carlos", "G1", "Hispanic surname (ambiguous)"),
    ("Okafor, Chukwu", "F2", "Nigerian Igbo surname"),
    ("Sharma, Rajesh", "D1", "North Indian surname"),
    ("Cohen, David", "C6", "Jewish surname"),
    ("Petrosyan, Tigran", "C7", "Armenian -yan suffix"),
    ("Beridze, Giorgi", "C8", "Georgian -dze suffix"),
    ("Diallo, Mamadou", "F1", "West African Francophone"),
]


# ===========================================================================
# PARAMETRIZED TESTS
# ===========================================================================


@pytest.mark.parametrize(
    "name,country_codes,expected,desc",
    REGION_TEST_CASES,
    ids=[f"{t[0]}({t[1][0]})->{t[2]}" for t in REGION_TEST_CASES],
)
def test_region_detection_with_country_code(
    manager, name, country_codes, expected, desc
):
    """Each name + CountryCode must detect the correct region."""
    entry = {"CanonicalLatin": name, "CountryCodes": country_codes}
    result = manager.detect_region(entry)
    assert result.region_code == expected, (
        f"{name} (CC={country_codes[0]}): expected {expected}, "
        f"got {result.region_code} (method={result.detection_method}) [{desc}]"
    )


@pytest.mark.parametrize(
    "name,country_codes,expected,desc",
    DIASPORA_CASES,
    ids=[f"diaspora-{t[0]}({t[1][0]})->{t[2]}" for t in DIASPORA_CASES],
)
def test_diaspora_ambiguous_names(manager, name, country_codes, expected, desc):
    """Ambiguous diaspora names must resolve correctly based on CC."""
    entry = {"CanonicalLatin": name, "CountryCodes": country_codes}
    result = manager.detect_region(entry)
    assert result.region_code == expected, (
        f"Diaspora: {name} (CC={country_codes[0]}): expected {expected}, "
        f"got {result.region_code} [{desc}]"
    )


@pytest.mark.parametrize(
    "name,country_codes,expected,desc",
    FEMALE_VARIANT_CASES,
    ids=[f"female-{t[0]}({t[1][0]})->{t[2]}" for t in FEMALE_VARIANT_CASES],
)
def test_female_name_variants(manager, name, country_codes, expected, desc):
    """Female name variants (-ova, -ova, -ska) must detect correctly."""
    entry = {"CanonicalLatin": name, "CountryCodes": country_codes}
    result = manager.detect_region(entry)
    assert result.region_code == expected, (
        f"Female: {name} (CC={country_codes[0]}): expected {expected}, "
        f"got {result.region_code} [{desc}]"
    )


@pytest.mark.parametrize(
    "name,country_codes,expected,desc",
    COMPOUND_NAME_CASES,
    ids=[f"compound-{t[0]}({t[1][0]})->{t[2]}" for t in COMPOUND_NAME_CASES],
)
def test_compound_names(manager, name, country_codes, expected, desc):
    """Compound/hyphenated/particle names must detect correctly."""
    entry = {"CanonicalLatin": name, "CountryCodes": country_codes}
    result = manager.detect_region(entry)
    assert result.region_code == expected, (
        f"Compound: {name} (CC={country_codes[0]}): expected {expected}, "
        f"got {result.region_code} [{desc}]"
    )


@pytest.mark.parametrize(
    "name,country_codes,expected,desc",
    SHORT_NAME_CASES,
    ids=[f"short-{t[0]}({t[1][0]})->{t[2]}" for t in SHORT_NAME_CASES],
)
def test_short_names(manager, name, country_codes, expected, desc):
    """Short 2-3 character surnames must detect correctly."""
    entry = {"CanonicalLatin": name, "CountryCodes": country_codes}
    result = manager.detect_region(entry)
    assert result.region_code == expected, (
        f"Short: {name} (CC={country_codes[0]}): expected {expected}, "
        f"got {result.region_code} [{desc}]"
    )


@pytest.mark.parametrize(
    "name,country_codes,expected,desc",
    DIACRITICS_CASES,
    ids=[f"diacrit-{t[0]}({t[1][0]})->{t[2]}" for t in DIACRITICS_CASES],
)
def test_diacritics_preserved(manager, name, country_codes, expected, desc):
    """Names with diacritics (or ASCII equivalents) must detect correctly."""
    entry = {"CanonicalLatin": name, "CountryCodes": country_codes}
    result = manager.detect_region(entry)
    assert result.region_code == expected, (
        f"Diacritics: {name} (CC={country_codes[0]}): expected {expected}, "
        f"got {result.region_code} [{desc}]"
    )


# ---------------------------------------------------------------------------
# Country code override test
# ---------------------------------------------------------------------------


def test_country_code_overrides_suffix_patterns(manager):
    """CountryCodes MUST override suffix matching. Euler+CH -> A2, not B1."""
    entry = {"CanonicalLatin": "Euler, Leonhard", "CountryCodes": ["CH"]}
    result = manager.detect_region(entry)
    assert result.region_code == "A2", f"Got {result.region_code} instead of A2"
    assert result.detection_method == "country-code"
    assert result.confidence >= 0.80


# ---------------------------------------------------------------------------
# Overall accuracy gate
# ---------------------------------------------------------------------------


def test_overall_accuracy_gate(manager):
    """Overall accuracy with CountryCodes must be >= 95%."""
    all_cases = (
        REGION_TEST_CASES
        + DIASPORA_CASES
        + FEMALE_VARIANT_CASES
        + COMPOUND_NAME_CASES
        + SHORT_NAME_CASES
        + DIACRITICS_CASES
    )
    correct = 0
    total = len(all_cases)
    failures = []
    for name, cc, expected, desc in all_cases:
        entry = {"CanonicalLatin": name, "CountryCodes": cc}
        result = manager.detect_region(entry)
        if result.region_code == expected:
            correct += 1
        else:
            failures.append(
                f"  {name} (CC={cc[0]}): expected {expected}, "
                f"got {result.region_code}"
            )
    accuracy = correct / total
    failure_detail = "\n".join(failures[:20])  # Show first 20
    assert accuracy >= 0.95, (
        f"Accuracy {accuracy:.1%} below 95% gate ({correct}/{total}).\n"
        f"First failures:\n{failure_detail}"
    )


# ---------------------------------------------------------------------------
# Region coverage
# ---------------------------------------------------------------------------


def test_all_37_regions_covered():
    """Verify test data covers all territory-mapped regions."""
    regions_tested = set()
    for _, _, expected, _ in REGION_TEST_CASES:
        regions_tested.add(expected)
    missing = REGIONS_WITH_TERRITORY_CODES - regions_tested
    assert not missing, (
        f"Missing region coverage for: {sorted(missing)}. "
        f"Covered {len(regions_tested)}: {sorted(regions_tested)}"
    )


def test_minimum_cases_per_region():
    """Each region must have at least 15 test cases."""
    from collections import Counter

    counts = Counter(t[2] for t in REGION_TEST_CASES)
    under = {r: c for r, c in counts.items() if c < 15}
    assert not under, (
        f"Regions with fewer than 15 cases: {under}. "
        f"Total cases: {len(REGION_TEST_CASES)}"
    )


# ---------------------------------------------------------------------------
# Detection without country codes
# ---------------------------------------------------------------------------


def test_detection_without_country_codes_still_works(manager):
    """Without CountryCodes, detection should still produce a valid result."""
    for name, expected, desc in NO_CC_CASES:
        entry = {"CanonicalLatin": name}
        result = manager.detect_region(entry)
        assert result.region_code is not None, f"No-CC: {name} returned None region"
        assert result.confidence > 0, f"No-CC: {name} returned 0 confidence"


def test_no_cc_accuracy_reasonable(manager):
    """Without CCs, at least 50% of well-known names should still detect."""
    correct = 0
    for name, expected, desc in NO_CC_CASES:
        entry = {"CanonicalLatin": name}
        result = manager.detect_region(entry)
        if result.region_code == expected:
            correct += 1
    accuracy = correct / len(NO_CC_CASES)
    assert (
        accuracy >= 0.50
    ), f"No-CC accuracy {accuracy:.1%} below 50% ({correct}/{len(NO_CC_CASES)})"


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


def test_empty_entry(manager):
    """Empty entry should return a valid result (not crash)."""
    result = manager.detect_region({"CanonicalLatin": ""})
    assert result.region_code is not None


def test_unknown_country_code_falls_through(manager):
    """Unknown country code (XX) should fall through gracefully."""
    entry = {"CanonicalLatin": "Smith, John", "CountryCodes": ["XX"]}
    result = manager.detect_region(entry)
    assert result.region_code is not None


def test_empty_country_codes(manager):
    """Empty CountryCodes list should fall through to pattern matching."""
    entry = {"CanonicalLatin": "Smith, John", "CountryCodes": []}
    result = manager.detect_region(entry)
    assert result.region_code is not None


def test_country_code_confidence_minimum(manager):
    """Country code detection must have confidence >= 0.80."""
    for name, cc, expected, _ in REGION_TEST_CASES[:10]:
        entry = {"CanonicalLatin": name, "CountryCodes": cc}
        result = manager.detect_region(entry)
        if result.detection_method == "country-code":
            assert (
                result.confidence >= 0.80
            ), f"{name}: confidence {result.confidence} < 0.80"
