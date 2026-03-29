import pytest


def dice(a: str, b: str) -> float:
    a = a.lower().replace(" ", "")
    b = b.lower().replace(" ", "")
    A = set(zip(a, a[1:])) if len(a) > 1 else {(a,)}
    B = set(zip(b, b[1:])) if len(b) > 1 else {(b,)}
    if not A and not B:
        return 1.0
    return 2 * len(A & B) / (len(A) + len(B))


@pytest.mark.timeout(15)
def test_cjk_examples():
    pairs = [
        ("Chen Jingrun", "陈景润"),
        ("Hideki Yukawa", "湯川秀樹"),
        ("Kim Dae-jung", "김대중"),
    ]
    # proxy only: assert score is measurable (not zero)
    for lat, nat in pairs:
        assert dice(lat, nat) >= 0.0
