from typing import Any, List

#!/usr/bin/env python3
"""
Comprehensive Edge Case Test Suite for GMNAP Pipeline

Real mathematician names covering all regions, scripts, edge cases.
This is what 39 tests should have been from the start.
"""

import json
import sys
import time
from typing import Dict

sys.path.insert(0, "src")

from src.core.pipeline import GMNAPPipeline


class ComprehensiveEdgeCaseTester:
    """Test suite with 200+ real mathematician names and edge cases."""

    def __init__(self):
        self.pipeline = GMNAPPipeline({"database_path": ":memory:"})
        self.results = {
            "total_tests": 0,
            "passed": 0,
            "failed": 0,
            "by_category": {},
            "failures": [],
        }

    def get_comprehensive_test_cases(self) -> List[Dict[str, Any]]:
        """Return 200+ comprehensive test cases with real mathematician names."""

        return [
            # ===== A1 ANGLO-SPHERE (30 cases) =====
            {
                "name": "Newton, Isaac",
                "expected_region": "A1",
                "category": "A1_Historical",
            },
            {
                "name": "Turing, Alan",
                "expected_region": "A1",
                "category": "A1_Historical",
            },
            {
                "name": "Hardy, Godfrey Harold",
                "expected_region": "A1",
                "category": "A1_Multiple_Names",
            },
            {
                "name": "Babbage, Charles",
                "expected_region": "A1",
                "category": "A1_Historical",
            },
            {
                "name": "Boole, George",
                "expected_region": "A1",
                "category": "A1_Historical",
            },
            {
                "name": "Hamilton, William Rowan",
                "expected_region": "A1",
                "category": "A1_Historical",
            },
            {
                "name": "Cayley, Arthur",
                "expected_region": "A1",
                "category": "A1_Historical",
            },
            {
                "name": "Sylvester, James Joseph",
                "expected_region": "A1",
                "category": "A1_Multiple_Names",
            },
            {
                "name": "De Morgan, Augustus",
                "expected_region": "A1",
                "category": "A1_Particle",
            },
            {
                "name": "O'Brien, Matthew",
                "expected_region": "A1",
                "category": "A1_Apostrophe",
            },
            {
                "name": "MacLaurin, Colin",
                "expected_region": "A1",
                "category": "A1_Scottish_Mac",
            },
            {
                "name": "MacDonald, Ian Grant",
                "expected_region": "A1",
                "category": "A1_Scottish_Mac",
            },
            {
                "name": "McShane, Edward James",
                "expected_region": "A1",
                "category": "A1_Irish_Mc",
            },
            {
                "name": "O'Connor, John Joseph",
                "expected_region": "A1",
                "category": "A1_Irish_O",
            },
            {
                "name": "FitzGerald, George Francis",
                "expected_region": "A1",
                "category": "A1_Compound",
            },
            {
                "name": "Smith-Volterra, John",
                "expected_region": "A1",
                "category": "A1_Hyphenated",
            },
            {
                "name": "Brown, Jr., Robert",
                "expected_region": "A1",
                "category": "A1_Suffix",
            },
            {
                "name": "White, Sr., William",
                "expected_region": "A1",
                "category": "A1_Suffix",
            },
            {
                "name": "Johnson III, Charles",
                "expected_region": "A1",
                "category": "A1_Numeral",
            },
            {
                "name": "Davis-Green, Mary",
                "expected_region": "A1",
                "category": "A1_Hyphenated_Female",
            },
            {"name": "SMITH, JOHN", "expected_region": "A1", "category": "A1_All_Caps"},
            {
                "name": "jones, william",
                "expected_region": "A1",
                "category": "A1_Lowercase",
            },
            {
                "name": "Thompson, Mary-Jane",
                "expected_region": "A1",
                "category": "A1_Hyphenated_Given",
            },
            {
                "name": "Williams, Jean-Paul",
                "expected_region": "A1",
                "category": "A1_French_Given",
            },
            {
                "name": "Anderson, D'Arcy",
                "expected_region": "A1",
                "category": "A1_Apostrophe_Given",
            },
            {
                "name": "Taylor, St. John",
                "expected_region": "A1",
                "category": "A1_Saint",
            },
            {
                "name": "Wilson, de la Mare",
                "expected_region": "A1",
                "category": "A1_Particle_Given",
            },
            {
                "name": "Miller, van der Berg",
                "expected_region": "A1",
                "category": "A1_Dutch_Given",
            },
            {
                "name": "Roberts, O'Malley",
                "expected_region": "A1",
                "category": "A1_Irish_Given",
            },
            {
                "name": "Lee, MacPherson",
                "expected_region": "A1",
                "category": "A1_Scottish_Given",
            },
            # ===== A2 WESTERN EUROPE (25 cases) =====
            {
                "name": "Gauss, Carl Friedrich",
                "expected_region": "A2",
                "category": "A2_German_Historical",
            },
            {
                "name": "Euler, Leonhard",
                "expected_region": "A2",
                "category": "A2_Swiss_Historical",
            },
            {
                "name": "Klein, Felix",
                "expected_region": "A2",
                "category": "A2_German_Historical",
            },
            {
                "name": "Riemann, Bernhard",
                "expected_region": "A2",
                "category": "A2_German_Historical",
            },
            {
                "name": "Weierstrass, Karl",
                "expected_region": "A2",
                "category": "A2_German_Historical",
            },
            {
                "name": "Kronecker, Leopold",
                "expected_region": "A2",
                "category": "A2_German_Historical",
            },
            {
                "name": "Dedekind, Richard",
                "expected_region": "A2",
                "category": "A2_German_Historical",
            },
            {
                "name": "Cantor, Georg",
                "expected_region": "A2",
                "category": "A2_German_Historical",
            },
            {
                "name": "Hilbert, David",
                "expected_region": "A2",
                "category": "A2_German_Historical",
            },
            {
                "name": "Noether, Emmy",
                "expected_region": "A2",
                "category": "A2_German_Female",
            },
            {
                "name": "Müller, Johannes",
                "expected_region": "A2",
                "category": "A2_German_Umlaut",
            },
            {
                "name": "Schröder, Ernst",
                "expected_region": "A2",
                "category": "A2_German_Umlaut",
            },
            {
                "name": "Möbius, August Ferdinand",
                "expected_region": "A2",
                "category": "A2_German_Umlaut",
            },
            {
                "name": "Weißmann, Karl",
                "expected_region": "A2",
                "category": "A2_German_Eszett",
            },
            {
                "name": "von Neumann, John",
                "expected_region": "A2",
                "category": "A2_German_Von",
            },
            {
                "name": "von Mises, Richard",
                "expected_region": "A2",
                "category": "A2_German_Von",
            },
            {
                "name": "van der Waerden, Bartel",
                "expected_region": "A2",
                "category": "A2_Dutch_Van",
            },
            {
                "name": "de Bruijn, Nicolaas",
                "expected_region": "A2",
                "category": "A2_Dutch_De",
            },
            {
                "name": "ter Haar, Dirk",
                "expected_region": "A2",
                "category": "A2_Dutch_Ter",
            },
            {
                "name": "Øystein, Øre",
                "expected_region": "A2",
                "category": "A2_Norwegian",
            },
            {"name": "Åhlfor, Lars", "expected_region": "A2", "category": "A2_Swedish"},
            {
                "name": "Ljunggren, Wilhelm",
                "expected_region": "A2",
                "category": "A2_Norwegian",
            },
            {"name": "Erdős, Pál", "expected_region": "A2", "category": "A2_Hungarian"},
            {
                "name": "Rényi, Alfréd",
                "expected_region": "A2",
                "category": "A2_Hungarian",
            },
            {
                "name": "König, Dénes",
                "expected_region": "A2",
                "category": "A2_Hungarian",
            },
            # ===== G1 LATIN AMERICA / IBERIAN (25 cases) =====
            {
                "name": "García, José",
                "expected_region": "G1",
                "category": "G1_Spanish_Common",
            },
            {
                "name": "González, María",
                "expected_region": "G1",
                "category": "G1_Spanish_Common",
            },
            {
                "name": "Rodríguez, Carlos",
                "expected_region": "G1",
                "category": "G1_Spanish_Accent",
            },
            {
                "name": "Martínez, Ana",
                "expected_region": "G1",
                "category": "G1_Spanish_Accent",
            },
            {
                "name": "López, Fernando",
                "expected_region": "G1",
                "category": "G1_Spanish_Common",
            },
            {
                "name": "Hernández, Luis",
                "expected_region": "G1",
                "category": "G1_Spanish_Common",
            },
            {
                "name": "Jiménez, Rosa",
                "expected_region": "G1",
                "category": "G1_Spanish_Accent",
            },
            {
                "name": "Ruíz, Diego",
                "expected_region": "G1",
                "category": "G1_Spanish_Accent",
            },
            {
                "name": "Díaz, Carmen",
                "expected_region": "G1",
                "category": "G1_Spanish_Accent",
            },
            {
                "name": "Moreno, Pablo",
                "expected_region": "G1",
                "category": "G1_Spanish_Common",
            },
            {
                "name": "Muñoz, Isabel",
                "expected_region": "G1",
                "category": "G1_Spanish_Enie",
            },
            {
                "name": "Álvarez, Miguel",
                "expected_region": "G1",
                "category": "G1_Spanish_Accent",
            },
            {
                "name": "Vázquez, Elena",
                "expected_region": "G1",
                "category": "G1_Spanish_Accent",
            },
            {
                "name": "Sánchez, Antonio",
                "expected_region": "G1",
                "category": "G1_Spanish_Accent",
            },
            {
                "name": "de la Cruz, Javier",
                "expected_region": "G1",
                "category": "G1_Spanish_Particle",
            },
            {
                "name": "del Río, Patricia",
                "expected_region": "G1",
                "category": "G1_Spanish_Particle",
            },
            {
                "name": "García-López, Manuel",
                "expected_region": "G1",
                "category": "G1_Spanish_Compound",
            },
            {
                "name": "Martín-González, Clara",
                "expected_region": "G1",
                "category": "G1_Spanish_Compound",
            },
            {
                "name": "Silva, João",
                "expected_region": "G1",
                "category": "G1_Portuguese",
            },
            {
                "name": "Santos, Maria",
                "expected_region": "G1",
                "category": "G1_Portuguese",
            },
            {
                "name": "Oliveira, Pedro",
                "expected_region": "G1",
                "category": "G1_Portuguese",
            },
            {
                "name": "Costa, Ana",
                "expected_region": "G1",
                "category": "G1_Portuguese",
            },
            {
                "name": "Pereira, Carlos",
                "expected_region": "G1",
                "category": "G1_Portuguese",
            },
            {
                "name": "Ferreira, Luís",
                "expected_region": "G1",
                "category": "G1_Portuguese_Accent",
            },
            {
                "name": "Almeida, José",
                "expected_region": "G1",
                "category": "G1_Portuguese",
            },
            # ===== B1 EAST SLAVIC (20 cases) =====
            {
                "name": "Chebyshev, Pafnuty",
                "expected_region": "B1",
                "category": "B1_Russian_Historical",
            },
            {
                "name": "Markov, Andrei",
                "expected_region": "B1",
                "category": "B1_Russian_Historical",
            },
            {
                "name": "Kolmogorov, Andrei",
                "expected_region": "B1",
                "category": "B1_Russian_Historical",
            },
            {
                "name": "Sobolev, Sergei",
                "expected_region": "B1",
                "category": "B1_Russian_Historical",
            },
            {
                "name": "Pontryagin, Lev",
                "expected_region": "B1",
                "category": "B1_Russian_Historical",
            },
            {
                "name": "Gelfand, Israel",
                "expected_region": "B1",
                "category": "B1_Russian_Historical",
            },
            {
                "name": "Vinogradov, Ivan",
                "expected_region": "B1",
                "category": "B1_Russian_Historical",
            },
            {
                "name": "Volkov, Sergei",
                "expected_region": "B1",
                "category": "B1_Russian_Pattern",
            },
            {
                "name": "Petrov, Vladimir",
                "expected_region": "B1",
                "category": "B1_Russian_Pattern",
            },
            {
                "name": "Smirnov, Dmitri",
                "expected_region": "B1",
                "category": "B1_Russian_Pattern",
            },
            {
                "name": "Kuznetsov, Alexander",
                "expected_region": "B1",
                "category": "B1_Russian_Pattern",
            },
            {
                "name": "Popov, Nikolai",
                "expected_region": "B1",
                "category": "B1_Russian_Pattern",
            },
            {
                "name": "Sergeev, Mikhail",
                "expected_region": "B1",
                "category": "B1_Russian_Pattern",
            },
            {
                "name": "Ivanova, Elena",
                "expected_region": "B1",
                "category": "B1_Russian_Female",
            },
            {
                "name": "Petrova, Maria",
                "expected_region": "B1",
                "category": "B1_Russian_Female",
            },
            {
                "name": "Volková, Anna",
                "expected_region": "B1",
                "category": "B1_Russian_Female",
            },
            {
                "name": "Shevchenko, Taras",
                "expected_region": "B1",
                "category": "B1_Ukrainian",
            },
            {
                "name": "Kovalenko, Ivan",
                "expected_region": "B1",
                "category": "B1_Ukrainian",
            },
            {
                "name": "Tkachenko, Olga",
                "expected_region": "B1",
                "category": "B1_Ukrainian",
            },
            {
                "name": "Lysenko, Viktor",
                "expected_region": "B1",
                "category": "B1_Ukrainian",
            },
            # ===== B2 SOUTH/CENTRAL SLAVIC (20 cases) =====
            {
                "name": "Čížek, Pavel",
                "expected_region": "B2",
                "category": "B2_Czech_Historical",
            },
            {
                "name": "Dvořák, František",
                "expected_region": "B2",
                "category": "B2_Czech_Historical",
            },
            {"name": "Hájek, Petr", "expected_region": "B2", "category": "B2_Czech"},
            {"name": "Novák, Jan", "expected_region": "B2", "category": "B2_Czech"},
            {"name": "Svoboda, Milan", "expected_region": "B2", "category": "B2_Czech"},
            {"name": "Černý, Jiří", "expected_region": "B2", "category": "B2_Czech"},
            {"name": "Kříž, Igor", "expected_region": "B2", "category": "B2_Czech"},
            {
                "name": "Kowalski, Janusz",
                "expected_region": "B2",
                "category": "B2_Polish",
            },
            {"name": "Nowak, Tomasz", "expected_region": "B2", "category": "B2_Polish"},
            {
                "name": "Wiśniewski, Piotr",
                "expected_region": "B2",
                "category": "B2_Polish",
            },
            {"name": "Wójcik, Anna", "expected_region": "B2", "category": "B2_Polish"},
            {
                "name": "Kowalczyk, Marek",
                "expected_region": "B2",
                "category": "B2_Polish",
            },
            {
                "name": "Lewandowski, Krzysztof",
                "expected_region": "B2",
                "category": "B2_Polish",
            },
            {
                "name": "Zieliński, Michał",
                "expected_region": "B2",
                "category": "B2_Polish",
            },
            {
                "name": "Horvát, János",
                "expected_region": "B2",
                "category": "B2_Hungarian_Slavic",
            },
            {"name": "Novák, Ján", "expected_region": "B2", "category": "B2_Slovak"},
            {"name": "Hodák, Martin", "expected_region": "B2", "category": "B2_Slovak"},
            {
                "name": "Jurčo, Branislav",
                "expected_region": "B2",
                "category": "B2_Slovak",
            },
            {"name": "Marić, Petar", "expected_region": "B2", "category": "B2_Serbian"},
            {
                "name": "Nikolić, Milan",
                "expected_region": "B2",
                "category": "B2_Serbian",
            },
            # ===== E1 CHINESE (15 cases) =====
            {
                "name": "Wang, Ming",
                "expected_region": "E1",
                "category": "E1_Chinese_Common",
            },
            {
                "name": "Li, Wei",
                "expected_region": "E1",
                "category": "E1_Chinese_Common",
            },
            {
                "name": "Zhang, Ping",
                "expected_region": "E1",
                "category": "E1_Chinese_Common",
            },
            {
                "name": "Liu, Jing",
                "expected_region": "E1",
                "category": "E1_Chinese_Common",
            },
            {
                "name": "Chen, Hong",
                "expected_region": "E1",
                "category": "E1_Chinese_Common",
            },
            {
                "name": "Yang, Lei",
                "expected_region": "E1",
                "category": "E1_Chinese_Common",
            },
            {
                "name": "Huang, Fang",
                "expected_region": "E1",
                "category": "E1_Chinese_Common",
            },
            {
                "name": "Zhao, Gang",
                "expected_region": "E1",
                "category": "E1_Chinese_Common",
            },
            {
                "name": "Wu, Jun",
                "expected_region": "E1",
                "category": "E1_Chinese_Common",
            },
            {
                "name": "Zhou, Hui",
                "expected_region": "E1",
                "category": "E1_Chinese_Common",
            },
            {
                "name": "Xu, Qiang",
                "expected_region": "E1",
                "category": "E1_Chinese_Common",
            },
            {
                "name": "Sun, Mei",
                "expected_region": "E1",
                "category": "E1_Chinese_Common",
            },
            {
                "name": "Ma, Long",
                "expected_region": "E1",
                "category": "E1_Chinese_Common",
            },
            {
                "name": "Zhu, Yan",
                "expected_region": "E1",
                "category": "E1_Chinese_Common",
            },
            {
                "name": "Guo, Tao",
                "expected_region": "E1",
                "category": "E1_Chinese_Common",
            },
            # ===== E3 JAPANESE (15 cases) =====
            {
                "name": "Tanaka, Hiroshi",
                "expected_region": "E3",
                "category": "E3_Japanese_Common",
            },
            {
                "name": "Suzuki, Yuki",
                "expected_region": "E3",
                "category": "E3_Japanese_Common",
            },
            {
                "name": "Takahashi, Kenji",
                "expected_region": "E3",
                "category": "E3_Japanese_Common",
            },
            {
                "name": "Yamamoto, Akira",
                "expected_region": "E3",
                "category": "E3_Japanese_Common",
            },
            {
                "name": "Watanabe, Satoshi",
                "expected_region": "E3",
                "category": "E3_Japanese_Common",
            },
            {
                "name": "Kobayashi, Yoko",
                "expected_region": "E3",
                "category": "E3_Japanese_Common",
            },
            {
                "name": "Nakamura, Takeshi",
                "expected_region": "E3",
                "category": "E3_Japanese_Common",
            },
            {
                "name": "Kato, Masako",
                "expected_region": "E3",
                "category": "E3_Japanese_Common",
            },
            {
                "name": "Sasaki, Naoki",
                "expected_region": "E3",
                "category": "E3_Japanese_Common",
            },
            {
                "name": "Shimizu, Ryoko",
                "expected_region": "E3",
                "category": "E3_Japanese_Common",
            },
            {
                "name": "Ito, Makoto",
                "expected_region": "E3",
                "category": "E3_Japanese_Common",
            },
            {
                "name": "Yoshida, Haruto",
                "expected_region": "E3",
                "category": "E3_Japanese_Common",
            },
            {
                "name": "Yamada, Sakura",
                "expected_region": "E3",
                "category": "E3_Japanese_Common",
            },
            {
                "name": "Matsumoto, Ren",
                "expected_region": "E3",
                "category": "E3_Japanese_Common",
            },
            {
                "name": "Inoue, Aoi",
                "expected_region": "E3",
                "category": "E3_Japanese_Common",
            },
            # ===== E4 KOREAN (15 cases) =====
            {
                "name": "Kim, Jong-Un",
                "expected_region": "E4",
                "category": "E4_Korean_Common",
            },
            {
                "name": "Lee, Min-Ho",
                "expected_region": "E4",
                "category": "E4_Korean_Common",
            },
            {
                "name": "Park, Soo-Jin",
                "expected_region": "E4",
                "category": "E4_Korean_Common",
            },
            {
                "name": "Choi, Young-Soo",
                "expected_region": "E4",
                "category": "E4_Korean_Common",
            },
            {
                "name": "Jung, Hye-Rim",
                "expected_region": "E4",
                "category": "E4_Korean_Common",
            },
            {
                "name": "Kang, Dong-Hyun",
                "expected_region": "E4",
                "category": "E4_Korean_Common",
            },
            {
                "name": "Cho, Mi-Young",
                "expected_region": "E4",
                "category": "E4_Korean_Common",
            },
            {
                "name": "Han, Seung-Ho",
                "expected_region": "E4",
                "category": "E4_Korean_Common",
            },
            {
                "name": "Jeong, Eun-Ji",
                "expected_region": "E4",
                "category": "E4_Korean_Common",
            },
            {
                "name": "Lim, Kyung-Soo",
                "expected_region": "E4",
                "category": "E4_Korean_Common",
            },
            {
                "name": "Yoon, Ji-Hoon",
                "expected_region": "E4",
                "category": "E4_Korean_Common",
            },
            {
                "name": "Jang, So-Young",
                "expected_region": "E4",
                "category": "E4_Korean_Common",
            },
            {
                "name": "Shin, Woo-Jin",
                "expected_region": "E4",
                "category": "E4_Korean_Common",
            },
            {
                "name": "Oh, Hee-Jung",
                "expected_region": "E4",
                "category": "E4_Korean_Common",
            },
            {
                "name": "Baek, Tae-Hyun",
                "expected_region": "E4",
                "category": "E4_Korean_Common",
            },
            # ===== C3 LEVANT/NILE ARABIC (15 cases) =====
            {
                "name": "Al-Hassan, Mohammed",
                "expected_region": "C3",
                "category": "C3_Arabic_Al",
            },
            {
                "name": "Al-Ahmad, Ahmed",
                "expected_region": "C3",
                "category": "C3_Arabic_Al",
            },
            {
                "name": "Al-Mahmoud, Omar",
                "expected_region": "C3",
                "category": "C3_Arabic_Al",
            },
            {
                "name": "Ibn Sina, Abdullah",
                "expected_region": "C3",
                "category": "C3_Arabic_Ibn",
            },
            {
                "name": "Ibn Rushd, Averroes",
                "expected_region": "C3",
                "category": "C3_Arabic_Ibn",
            },
            {
                "name": "Abu Bakr, Khalid",
                "expected_region": "C3",
                "category": "C3_Arabic_Abu",
            },
            {
                "name": "Abu Nasr, Farabi",
                "expected_region": "C3",
                "category": "C3_Arabic_Abu",
            },
            {
                "name": "Abd Rahman, Ali",
                "expected_region": "C3",
                "category": "C3_Arabic_Abd",
            },
            {
                "name": "Abd Allah, Hassan",
                "expected_region": "C3",
                "category": "C3_Arabic_Abd",
            },
            {
                "name": "Bin Laden, Osama",
                "expected_region": "C3",
                "category": "C3_Arabic_Bin",
            },
            {
                "name": "Bin Rashid, Mohammed",
                "expected_region": "C3",
                "category": "C3_Arabic_Bin",
            },
            {
                "name": "El-Sayed, Mahmoud",
                "expected_region": "C3",
                "category": "C3_Arabic_El",
            },
            {
                "name": "El-Masri, Youssef",
                "expected_region": "C3",
                "category": "C3_Arabic_El",
            },
            {
                "name": "Nasir, Ahmed",
                "expected_region": "C3",
                "category": "C3_Arabic_Simple",
            },
            {
                "name": "Khalil, Sara",
                "expected_region": "C3",
                "category": "C3_Arabic_Simple",
            },
            # ===== D1 SOUTH ASIA (15 cases) =====
            {
                "name": "Sharma, Rajesh",
                "expected_region": "D1",
                "category": "D1_Hindi_Common",
            },
            {
                "name": "Patel, Priya",
                "expected_region": "D1",
                "category": "D1_Gujarati",
            },
            {"name": "Singh, Amrit", "expected_region": "D1", "category": "D1_Sikh"},
            {
                "name": "Kumar, Anand",
                "expected_region": "D1",
                "category": "D1_Hindi_Common",
            },
            {
                "name": "Gupta, Ravi",
                "expected_region": "D1",
                "category": "D1_Hindi_Common",
            },
            {
                "name": "Agarwal, Sneha",
                "expected_region": "D1",
                "category": "D1_Hindi_Common",
            },
            {"name": "Jain, Vikash", "expected_region": "D1", "category": "D1_Jain"},
            {
                "name": "Reddy, Srinivas",
                "expected_region": "D1",
                "category": "D1_Telugu",
            },
            {"name": "Rao, Venkata", "expected_region": "D1", "category": "D1_Telugu"},
            {"name": "Iyer, Ramesh", "expected_region": "D1", "category": "D1_Tamil"},
            {
                "name": "Nair, Lakshmi",
                "expected_region": "D1",
                "category": "D1_Malayalam",
            },
            {"name": "Das, Subhash", "expected_region": "D1", "category": "D1_Bengali"},
            {"name": "Ghosh, Tapan", "expected_region": "D1", "category": "D1_Bengali"},
            {
                "name": "Mukherjee, Indira",
                "expected_region": "D1",
                "category": "D1_Bengali",
            },
            {
                "name": "Chatterjee, Anirban",
                "expected_region": "D1",
                "category": "D1_Bengali",
            },
            # ===== EDGE CASES & STRESS TESTS (35 cases) =====
            # Length extremes
            {"name": "Li, A", "expected_region": "E1", "category": "Edge_Short_Name"},
            {"name": "O, B", "expected_region": "A1", "category": "Edge_Single_Letter"},
            {
                "name": "Wolfeschlegelsteinhausenbergerdorff, Johann",
                "expected_region": "A2",
                "category": "Edge_Long_German",
            },
            {
                "name": "García-López-Martínez-González, María-Carmen-Isabel-Rosa",
                "expected_region": "G1",
                "category": "Edge_Very_Long_Spanish",
            },
            # Multiple particles and prefixes
            {
                "name": "von und zu Liechtenstein, Hans",
                "expected_region": "A2",
                "category": "Edge_Multiple_Particles",
            },
            {
                "name": "de la Rosa y González, Carmen",
                "expected_region": "G1",
                "category": "Edge_Multiple_Spanish_Particles",
            },
            {
                "name": "van der Berg ten Broek, Willem",
                "expected_region": "A2",
                "category": "Edge_Multiple_Dutch_Particles",
            },
            # Mixed case and formatting
            {
                "name": "mCdOnAlD, rOnAlD",
                "expected_region": "A1",
                "category": "Edge_Mixed_Case",
            },
            {
                "name": "O'CONNOR, PATRICK",
                "expected_region": "A1",
                "category": "Edge_All_Caps_Apostrophe",
            },
            {
                "name": "d'alembert, jean",
                "expected_region": "A2",
                "category": "Edge_Lowercase_French",
            },
            # Multiple apostrophes and hyphens
            {
                "name": "O'Connor-O'Brien, Seán",
                "expected_region": "A1",
                "category": "Edge_Multiple_Apostrophes",
            },
            {
                "name": "Mary-Ann-Elizabeth, Smith-Jones-Brown",
                "expected_region": "A1",
                "category": "Edge_Multiple_Hyphens",
            },
            # Roman numerals and suffixes
            {
                "name": "Smith IV, John",
                "expected_region": "A1",
                "category": "Edge_Roman_Numeral",
            },
            {
                "name": "Brown VIII, William",
                "expected_region": "A1",
                "category": "Edge_Roman_Numeral",
            },
            {
                "name": "Johnson, Jr., Robert",
                "expected_region": "A1",
                "category": "Edge_Jr_Comma",
            },
            # Titles and honorifics (should be handled or rejected)
            {
                "name": "Dr. Smith, John",
                "expected_region": "A1",
                "category": "Edge_Title_Prefix",
                "should_fail": True,
            },
            {
                "name": "Smith, Dr. John",
                "expected_region": "A1",
                "category": "Edge_Title_Given",
            },
            {
                "name": "Prof. García, José",
                "expected_region": "G1",
                "category": "Edge_Prof_Title",
                "should_fail": True,
            },
            # Numbers in names (should fail)
            {
                "name": "Smith2, John",
                "expected_region": "A1",
                "category": "Edge_Number_Surname",
                "should_fail": True,
            },
            {
                "name": "Smith, John3",
                "expected_region": "A1",
                "category": "Edge_Number_Given",
                "should_fail": True,
            },
            {
                "name": "Sm1th, J0hn",
                "expected_region": "A1",
                "category": "Edge_Leet_Speak",
                "should_fail": True,
            },
            # Special characters that should fail
            {
                "name": "Smith@gmail, John",
                "expected_region": "A1",
                "category": "Edge_Email_Symbol",
                "should_fail": True,
            },
            {
                "name": "Smith#tag, John",
                "expected_region": "A1",
                "category": "Edge_Hash_Symbol",
                "should_fail": True,
            },
            {
                "name": "Smith$money, John",
                "expected_region": "A1",
                "category": "Edge_Dollar_Symbol",
                "should_fail": True,
            },
            {
                "name": "Smith%percent, John",
                "expected_region": "A1",
                "category": "Edge_Percent_Symbol",
                "should_fail": True,
            },
            # Unicode edge cases
            {
                "name": "Müller-Öström, Åse",
                "expected_region": "A2",
                "category": "Edge_Multiple_Diacritics",
            },
            {
                "name": "Żółć, Jaśń",
                "expected_region": "B2",
                "category": "Edge_Polish_Special",
            },
            {
                "name": "Dvořák-Černý, Václav",
                "expected_region": "B2",
                "category": "Edge_Czech_Compound",
            },
            # Boundary length cases
            {
                "name": "A" * 50 + ", " + "B" * 50,
                "expected_region": "A1",
                "category": "Edge_Max_Length",
                "should_fail": True,
            },
            {
                "name": "",
                "expected_region": "A1",
                "category": "Edge_Empty_String",
                "should_fail": True,
            },
            {
                "name": ", ",
                "expected_region": "A1",
                "category": "Edge_Just_Comma",
                "should_fail": True,
            },
            {
                "name": "Smith,",
                "expected_region": "A1",
                "category": "Edge_Missing_Given",
                "should_fail": True,
            },
            {
                "name": ", John",
                "expected_region": "A1",
                "category": "Edge_Missing_Surname",
                "should_fail": True,
            },
            # Stress test with valid complex cases
            {
                "name": "Ibn al-Haytham al-Basri, Abu Ali Hassan",
                "expected_region": "C3",
                "category": "Edge_Complex_Arabic",
            },
            {
                "name": "Ramanujan Iyengar, Srinivasa",
                "expected_region": "D1",
                "category": "Edge_Complex_Indian",
            },
            {
                "name": "Gauss-Lobachevsky-Bolyai, Johann-Nikolai-Wolfgang",
                "expected_region": "A2",
                "category": "Edge_Complex_European",
            },
        ]

    def run_comprehensive_tests(self):
        """Run all comprehensive edge case tests."""
        test_cases = self.get_comprehensive_test_cases()
        self.results["total_tests"] = len(test_cases)

        print("🚀 COMPREHENSIVE EDGE CASE TEST SUITE")
        print("=" * 60)
        print(f"Testing {len(test_cases)} real mathematician names + edge cases")
        print("=" * 60)

        start_time = time.time()

        for i, test_case in enumerate(test_cases, 1):
            name = test_case["name"]
            expected_region = test_case["expected_region"]
            category = test_case["category"]
            should_fail = test_case.get("should_fail", False)

            # Track by category
            if category not in self.results["by_category"]:
                self.results["by_category"][category] = {
                    "passed": 0,
                    "failed": 0,
                    "total": 0,
                }

            self.results["by_category"][category]["total"] += 1

            print(f"[{i:3d}/{len(test_cases)}] {category}: {name[:50]}", end="")
            if len(name) > 50:
                print("...", end="")

            try:
                result = self.pipeline.process_entry({"CanonicalLatin": name})
                actual_region = result.get("RegionCode", "UNKNOWN")

                if should_fail:
                    # This should have failed but passed
                    self.results["failed"] += 1
                    self.results["by_category"][category]["failed"] += 1
                    self.results["failures"].append(
                        {
                            "name": name,
                            "category": category,
                            "expected": "FAILURE",
                            "actual": f"SUCCESS ({actual_region})",
                            "issue": "Should have failed but passed",
                        }
                    )
                    print(" FAIL SHOULD HAVE FAILED")
                elif actual_region == expected_region:
                    # Correct
                    self.results["passed"] += 1
                    self.results["by_category"][category]["passed"] += 1
                    print(f" PASS {actual_region}")
                else:
                    # Wrong region
                    self.results["failed"] += 1
                    self.results["by_category"][category]["failed"] += 1
                    self.results["failures"].append(
                        {
                            "name": name,
                            "category": category,
                            "expected": expected_region,
                            "actual": actual_region,
                            "issue": "Wrong region detected",
                        }
                    )
                    print(f" FAIL {actual_region} (expected {expected_region})")

            except Exception as e:
                if should_fail:
                    # Correctly failed
                    self.results["passed"] += 1
                    self.results["by_category"][category]["passed"] += 1
                    print(f" PASS CORRECTLY FAILED: {str(e)[:30]}...")
                else:
                    # Unexpected failure
                    self.results["failed"] += 1
                    self.results["by_category"][category]["failed"] += 1
                    self.results["failures"].append(
                        {
                            "name": name,
                            "category": category,
                            "expected": expected_region,
                            "actual": f"ERROR: {str(e)}",
                            "issue": "Unexpected failure",
                        }
                    )
                    print(f" FAIL ERROR: {str(e)[:30]}...")

        elapsed = time.time() - start_time
        self.print_results(elapsed)

    def print_results(self, elapsed_time: float):
        """Print comprehensive test results."""
        print("\n" + "=" * 60)
        print("📊 COMPREHENSIVE TEST RESULTS")
        print("=" * 60)

        total = self.results["total_tests"]
        passed = self.results["passed"]
        failed = self.results["failed"]
        pass_rate = (passed / total * 100) if total > 0 else 0

        print(f"Total Tests: {total}")
        print(f"Passed: {passed} ({pass_rate:.1f}%)")
        print(f"Failed: {failed}")
        print(f"Time: {elapsed_time:.2f}s ({total/elapsed_time:.1f} tests/sec)")

        # Results by category
        print("\n📋 RESULTS BY CATEGORY:")
        print("-" * 60)
        for category, stats in sorted(self.results["by_category"].items()):
            total_cat = stats["total"]
            passed_cat = stats["passed"]
            rate = (passed_cat / total_cat * 100) if total_cat > 0 else 0
            print(f"{category:35} {passed_cat:2d}/{total_cat:2d} ({rate:5.1f}%)")

        # Show failures
        if self.results["failures"]:
            print(f"\nFAIL FAILURES ({len(self.results['failures'])}):")
            print("-" * 60)
            for i, failure in enumerate(
                self.results["failures"][:20], 1
            ):  # Show first 20
                print(f"{i:2d}. {failure['name'][:40]}")
                print(
                    f"    {failure['category']}: Expected {failure['expected']}, got {failure['actual']}"
                )
                print(f"    Issue: {failure['issue']}")

            if len(self.results["failures"]) > 20:
                print(f"    ... and {len(self.results['failures']) - 20} more failures")

        # Save detailed results
        with open("comprehensive_test_results.json", "w") as f:
            json.dump(self.results, f, indent=2)

        print("\n💾 Detailed results saved to comprehensive_test_results.json")


if __name__ == "__main__":
    tester = ComprehensiveEdgeCaseTester()
    tester.run_comprehensive_tests()
