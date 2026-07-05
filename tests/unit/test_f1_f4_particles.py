"""Spec §2 F1/F4 distinct_features — French & Portuguese particles (R50).

Both processors were stubs (clean() ended in `pass` / plain-strip;
order_key sorted on the raw string). Now: in-name particles are
lowercase-normalised, extracted into RegionalExtras (F1), and excluded
from the collation key.
"""

import pytest

from src.regions.f_groups.f1_ssa_francophone.processor import F1_SSAFrancophone
from src.regions.f_groups.f4_lusophone_africa.processor import F4_LusophoneAfrica


@pytest.mark.timeout(30)
def test_f1_french_particles_normalised_and_extracted():
    p = F1_SSAFrancophone()
    e = {"CanonicalLatin": "de la Croix, Jean DE LA Salle"}
    p.clean(e)
    assert e["CanonicalLatin"] == "de la Croix, Jean de la Salle"
    p.augment(e)
    extras = e["RegionalExtras"]
    assert extras["family_particle"] == "de la"
    assert extras["family_core"] == "Croix"
    assert p.order_key(e) == "croix"  # particle-excluded collation


@pytest.mark.timeout(30)
def test_f1_no_particle_name_unchanged():
    p = F1_SSAFrancophone()
    e = {"CanonicalLatin": "Diallo, Amadou"}
    p.clean(e)
    assert e["CanonicalLatin"] == "Diallo, Amadou"
    assert p.order_key(e) == "diallo"


@pytest.mark.timeout(30)
def test_f4_portuguese_particles_normalised_and_collated():
    p = F4_LusophoneAfrica()
    e = {"CanonicalLatin": "dos Santos, Maria DA Silva"}
    p.clean(e)
    assert e["CanonicalLatin"] == "dos Santos, Maria da Silva"
    assert p.order_key(e) == "SANTOS"


@pytest.mark.timeout(30)
def test_f4_no_particle_name_unchanged():
    p = F4_LusophoneAfrica()
    e = {"CanonicalLatin": "Machel, Graça"}
    p.clean(e)
    assert p.order_key(e) == "MACHEL"
