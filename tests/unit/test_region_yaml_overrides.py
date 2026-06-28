"""Region YAML overrides are a LIVE extension point (R39 activation).

RegionSpec.load_yaml_config() reads config/regions/<code>.yaml and was
previously dormant — no processor called it and config/regions/ didn't
exist. A2_WesternEurope now consumes it: it merges germanic/romance
particle lists from config/regions/a2.yaml into its hardcoded defaults.
"""

import pytest

from src.regions import base as region_base
from src.regions.base import RegionSpec


def _fresh_a2():
    RegionSpec.clear_yaml_cache()
    from src.regions.a_groups.a2_western_europe.processor import A2_WesternEurope

    return A2_WesternEurope()


def test_committed_a2_yaml_override_is_live():
    """The committed config/regions/a2.yaml reaches a real A2 instance."""
    RegionSpec.clear_yaml_cache()
    a = _fresh_a2()
    # particles added ONLY via config/regions/a2.yaml
    assert "vom" in a.particles
    assert "dei" in a.particles
    RegionSpec.clear_yaml_cache()


def test_yaml_override_merges_custom_particles(tmp_path, monkeypatch):
    """A region YAML is loaded and merged into self.particles."""
    cfgdir = tmp_path / "regions"
    cfgdir.mkdir()
    (cfgdir / "a2.yaml").write_text(
        "germanic_particles:\n  - vanden\nromance_particles:\n  - degli\n"
    )
    monkeypatch.setattr(region_base, "_REGION_CONFIG_DIR", cfgdir)
    a = _fresh_a2()
    assert "vanden" in a.particles
    assert "degli" in a.particles
    # hardcoded defaults are preserved alongside the overrides
    assert "von" in a.particles and "di" in a.particles
    RegionSpec.clear_yaml_cache()


def test_yaml_override_absent_keeps_defaults(tmp_path, monkeypatch):
    """No YAML file for the region -> hardcoded defaults only (control)."""
    cfgdir = tmp_path / "regions"
    cfgdir.mkdir()  # empty: no a2.yaml here
    monkeypatch.setattr(region_base, "_REGION_CONFIG_DIR", cfgdir)
    a = _fresh_a2()
    assert "von" in a.particles  # a hardcoded default
    assert "vom" not in a.particles  # the committed override is NOT seen
    RegionSpec.clear_yaml_cache()


def test_load_yaml_config_never_raises_on_bad_yaml(tmp_path, monkeypatch):
    """A malformed YAML degrades to {} (the processor must never crash)."""
    cfgdir = tmp_path / "regions"
    cfgdir.mkdir()
    (cfgdir / "a2.yaml").write_text(": : : not valid : [\n")
    monkeypatch.setattr(region_base, "_REGION_CONFIG_DIR", cfgdir)
    a = _fresh_a2()  # must not raise
    assert "von" in a.particles  # defaults intact
    RegionSpec.clear_yaml_cache()
