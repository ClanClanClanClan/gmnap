"""Authority fetchers must reference real FetchStatus members and build
valid FetchResults (R39).

The live tier-1 HAL fetcher used FetchStatus.ERROR (no such member) and
passed source=/query=/error= kwargs that FetchResult doesn't accept — so
at OFFLINE=0 every HAL fetch raised AttributeError (in the except block
itself) or TypeError. This guards against that whole class.
"""

from __future__ import annotations

import ast
import dataclasses
import pathlib
import re

import pytest

from src.authorities.base import AuthorityData, FetchResult, FetchStatus

# Map the dataclass name -> set of its real field names. Derived from the
# dataclass itself (not hardcoded) so it stays correct as fields are added.
_VALIDATED_CTORS = {
    "FetchResult": {f.name for f in dataclasses.fields(FetchResult)},
    "AuthorityData": {f.name for f in dataclasses.fields(AuthorityData)},
}


def _ctor_name(call: ast.Call) -> str | None:
    """Return 'FetchResult'/'AuthorityData' if this Call constructs one,
    whether referenced bare (``FetchResult(...)``) or qualified
    (``base.FetchResult(...)``)."""
    func = call.func
    if isinstance(func, ast.Name):
        return func.id if func.id in _VALIDATED_CTORS else None
    if isinstance(func, ast.Attribute):
        return func.attr if func.attr in _VALIDATED_CTORS else None
    return None


def test_fetchresult_and_authoritydata_constructions_use_valid_fields():
    """Every FetchResult(...)/AuthorityData(...) construction under
    src/authorities/ must pass ONLY real dataclass field names.

    This is the strongest guard against the HAL-class bug (R39/R40): six
    tier-1 fetchers (acm, ieee, pubmed, springer, viaf, wiley) passed
    source=/query=/error= to FetchResult and identifier=/name=/variants=/
    external_ids=/confidence=/publications= to AuthorityData — none of which
    are fields — so EVERY call raised TypeError. The regex FetchStatus test
    below only caught the enum-member half; this AST test catches the
    constructor-kwarg half on ALL code paths (success, not-found, error,
    auth-failed), not just the ones a runtime test happens to exercise.
    """
    offenders = []
    for path in sorted(pathlib.Path("src/authorities").rglob("*.py")):
        tree = ast.parse(path.read_text(), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            ctor = _ctor_name(node)
            if ctor is None:
                continue
            valid = _VALIDATED_CTORS[ctor]
            for kw in node.keywords:
                if kw.arg is None:  # **kwargs splat — can't check statically
                    continue
                if kw.arg not in valid:
                    offenders.append(
                        f"{path}:{node.lineno} {ctor}(...{kw.arg}=...) "
                        f"— not a field of {ctor} (valid: {sorted(valid)})"
                    )
    assert not offenders, "invalid constructor kwargs:\n  " + "\n  ".join(offenders)


def test_all_authority_fetchers_are_concrete():
    """Every *Fetcher subclass of AuthorityFetcher must implement ALL its
    abstract methods (fetch + parse_response).

    PubMed and VIAF shipped without parse_response, so they stayed abstract:
    `PubMedFetcher(...)` / `VIAFFetcher(...)` raised
    `TypeError: Can't instantiate abstract class ... with abstract method
    parse_response`. The class was completely unusable, not merely buggy on
    one code path — and no other test caught it because none constructed
    them. This guards the whole roster.
    """
    import importlib
    import inspect

    from src.authorities.base import AuthorityFetcher

    abstract_offenders = []
    for path in sorted(pathlib.Path("src/authorities").rglob("*.py")):
        if path.name in ("base.py", "__init__.py"):
            continue
        mod_name = ".".join(path.with_suffix("").parts)
        try:
            mod = importlib.import_module(mod_name)
        except Exception:
            # Optional-dependency import failures are out of scope for this
            # check (a separate concern); the FetchResult/FetchStatus tests
            # operate on source text and don't need the import to succeed.
            continue
        for _, cls in inspect.getmembers(mod, inspect.isclass):
            if (
                issubclass(cls, AuthorityFetcher)
                and cls is not AuthorityFetcher
                and cls.__module__ == mod.__name__
                and inspect.isabstract(cls)
            ):
                abstract_offenders.append(
                    f"{mod_name}.{cls.__name__} missing "
                    f"{sorted(cls.__abstractmethods__)}"
                )
    assert (
        not abstract_offenders
    ), "fetcher subclasses left abstract (uninstantiable):\n  " + "\n  ".join(
        abstract_offenders
    )


def test_all_fetchstatus_references_are_valid_members():
    """Every FetchStatus.X referenced under src/authorities/ must exist —
    a missing one makes a fetcher's error handler itself raise
    AttributeError on every failure."""
    valid = set(FetchStatus.__members__)
    bad = []
    for p in pathlib.Path("src/authorities").rglob("*.py"):
        for m in set(re.findall(r"FetchStatus\.([A-Z_]+)", p.read_text())):
            if m not in valid:
                bad.append(f"{p}:{m}")
    assert not bad, f"non-existent FetchStatus members referenced: {sorted(bad)}"


def test_fetchstatus_has_generic_error_member():
    assert hasattr(FetchStatus, "ERROR")


@pytest.mark.asyncio
async def test_hal_fetch_error_path_returns_result():
    """HAL's except block must return a FetchResult, not raise."""
    from src.authorities.tier1.hal import HALFetcher

    f = HALFetcher()

    async def _boom(*a, **k):
        raise RuntimeError("network down")

    f._search_author = _boom
    res = await f.fetch("Euler, Leonhard")
    assert res.status == FetchStatus.ERROR
    assert "network down" in (res.error_message or "")
    assert isinstance(res, FetchResult)


@pytest.mark.asyncio
async def test_hal_fetch_not_found_path_returns_result():
    from src.authorities.tier1.hal import HALFetcher

    f = HALFetcher()

    async def _empty(*a, **k):
        return []

    f._search_author = _empty
    res = await f.fetch("Nobody Here")
    assert res.status == FetchStatus.NOT_FOUND
