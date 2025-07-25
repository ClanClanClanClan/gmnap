#!/bin/bash
# Add more common given name syllables that are missing

echo "Adding common given name syllables..."

# Common given name syllables that might be missing
cat >> resources/rr_syllable_map.csv << EOF
래,rae
례,rye
뢰,roe
봉,bong
숙,suk
순,soon
슬,seul
실,sil
아,ah
완,wan
요,yo
윤,yun
율,yul
응,eung
의,ui
익,ik
츠,tsu
EOF

echo "Done adding syllables"