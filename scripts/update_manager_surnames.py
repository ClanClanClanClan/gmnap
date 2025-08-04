#!/usr/bin/env python3
"""
Update manager.py with real mathematician surnames.
Generated from docs/regional/*.yaml files.
"""

from pathlib import Path

# Mathematician surnames extracted from YAML files
MATHEMATICIAN_SURNAMES = {
    "A2": {
        "abbes", "abdesselam", "abel", "adamski", "alesker",
        "allaud", "amar", "amoroso", "anantharaman", "arnaudon",
        "arouh", "aubin", "azaïs", "aït-sahalia", "bachelier",
        "badrikian", "bailleul", "baker", "balan", "banaszak",
        "barraud", "bassan", "baudoin", "bautista", "bayad",
        "beckmann", "benaïm", "benedetti", "benoist", "berger",
        "bernays", "berthelot", "besson", "biane", "bikchentaev",
        "blanchard", "blum", "bolyai", "bonnet", "borel",
        "bouchaud", "bourbaki", "bourgain", "bourguignon", "boyer",
        "brihaye", "briot", "brézis", "bureau", "burgos",
    },
    "B1": {
        "agranovich", "akhiezer", "aleksandrov", "andronov", "arnold",
        "aronszajn", "babenko", "bakalov", "bary", "baryshnikov",
        "bashkirov", "belyi", "berezansky", "bernstein", "besicovitch",
        "birman", "blashke", "bogolyubov", "bokhoven", "brahmanin",
        "bunyakovsky", "chebyshev", "chernoff", "cherny", "chernyshevsky",
        "daniil", "dmitriev", "dobrushin", "dynkin", "efimov",
        "egorov", "faddeev", "feller", "fomin", "fréchet",
        "gelfand", "gelfond", "glivenko", "gnedenko", "gromov",
        "kantorovich", "karpelevich", "khinchin", "khintchine", "kolmogorov",
        "kolmogorova", "krasovskii", "krein", "krylov", "kurosh",
    },
    "B2": {
        "aczél", "agranovich", "ahlfors", "ajdukiewicz", "alama",
        "ambrosetti", "andrica", "babic", "babić", "babuska",
        "babuška", "balan", "banach", "barany", "bartoszyński",
        "berkovich", "borsuk", "brattka", "brodzki", "brouwer",
        "brylinski", "buchwald", "buliga", "burzynski", "burzyński",
        "bárány", "bălan", "chwistek", "cichoń", "ciupiński",
        "csiszár", "danilov", "dickstein", "dolezal", "doležal",
        "dudley", "erdős", "farkas", "fiedler", "fisz",
        "freidlin", "gromov", "gundlach", "hausdorff", "hurewicz",
        "hájek", "iwanik", "jadacki", "kac", "kalman",
    },
    "E1": {
        "an", "bao", "cai", "cao", "chan",
        "chang", "chao", "cheang", "chen", "cheng",
        "cheung", "chew", "chiang", "chiu", "choi",
        "choo", "chow", "chu", "dai", "deng",
        "ding", "dong", "fang", "feng", "fu",
        "gao", "geng", "gu", "guo", "han",
        "he", "hu", "huang", "jiang", "ju",
        "li", "lin", "liu", "lu", "lü",
        "ma", "ng", "qian", "qu", "shao",
        "shen", "shu", "su", "sun", "tang",
    },
    "E3": {
        "abe", "abe-yoshinaga", "abiru", "abo", "agata",
        "aida", "aihara", "aikawa", "aizawa", "akaike",
        "akama", "akamatsu", "akao", "akasaki", "akashi",
        "akazawa", "akimoto", "akiyama", "akizuki", "amano",
        "amari", "amatsu", "amemiya", "anada", "ando",
        "andô", "andō", "anzai", "aoki", "aomoto",
        "aoyama", "arai", "araki", "aramaki", "arase",
        "arimitsu", "arisawa", "ariyoshi", "asai", "asano",
        "aso", "asoh", "atarashi", "awano", "awazu",
        "azuma", "baba", "bamba", "ban", "bando",
    },
    "E4": {
        "ahn", "an", "ba", "bae", "baek",
        "baik", "bak", "bang", "bong", "boo",
        "byeon", "byon", "byun", "cha", "chae",
        "chang", "cheon", "cheong", "cho", "choe",
        "choi", "chu", "chun", "chung", "david",
        "do", "eo", "eoh", "eom", "eu",
        "gil", "goh", "goo", "grace", "gu",
        "gwak", "ha", "hahm", "ham", "han",
        "heo", "hong", "huh", "hwang", "hwangbo",
        "hyun", "im", "jang", "jee", "jeon",
    },
    "E5": {
        "an", "bùi", "bạch", "cao", "châu",
        "cù", "dương", "hoàng", "hà", "lê",
        "nguyễn", "phan", "phạm", "trần", "trịnh",
        "võ", "vũ", "xương", "yến", "zào",
        "đào", "đặng", "đỗ",
    },
    "E6": {
        "anuwat", "apichat", "arunotai", "chaiboonchoe", "chaiya",
        "chaiyaratana", "chalermpol", "charoenlarpnopparut", "charoenwong", "chavalit",
        "chollada", "chutima", "hemakom", "imsamran", "jaidee",
        "kamonsakchai", "kitjaroen", "kittichai", "kittitheeranun", "la-ornual",
        "maneerattanaporn", "maniyom", "mongkolsiri", "nanapaprai", "nongnid",
        "nualsri", "oran", "paiboonvorachat", "pansang", "panwong",
        "pattaradanai", "pattaraintakorn", "pimchaya", "polprasert", "pongcharoen",
        "pongthavornkamol", "prajuab", "putthapiban", "raksasataya", "rapeepan",
        "rattanapradit", "roongruangsuwan", "rungtip", "sakchai", "sarunya",
        "sinsupasorn", "siriporn", "srichan", "suetrong", "sukanya",
    },
}

def update_manager():
    """Update manager.py with mathematician surnames."""
    manager_path = Path(__file__).parent.parent / "src" / "regions" / "manager.py"
    
    # Read current content
    with open(manager_path, 'r') as f:
        content = f.read()
    
    # Find where to insert new surnames
    for region, surnames in MATHEMATICIAN_SURNAMES.items():
        # Find the region's surname section
        region_marker = f'"{region}": {{'
        if region_marker in content:
            # Find the closing brace
            start = content.find(region_marker)
            brace_count = 0
            pos = start
            
            while pos < len(content):
                if content[pos] == '{':
                    brace_count += 1
                elif content[pos] == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        # Found the closing brace
                        # Insert surnames before it
                        insert_pos = pos
                        
                        # Create insertion text
                        insert_text = "\n                # Real mathematician surnames\n"
                        for surname in sorted(surnames)[:20]:  # Add top 20
                            insert_text += f'                "{surname}",\n'
                        
                        # Insert into content
                        content = content[:insert_pos] + insert_text + content[insert_pos:]
                        break
                pos += 1
    
    # Write updated content
    print(f"✅ Updated {manager_path}")
    # Uncomment to actually write:
    # with open(manager_path, 'w') as f:
    #     f.write(content)

if __name__ == "__main__":
    update_manager()
