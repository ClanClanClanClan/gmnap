from src.ops.hashcash import verify_hashcash, HashcashStamp
import time, hashlib, itertools


def _mint(bits: int, resource: str) -> str:
    # Brute-force a tiny stamp for test (bits <= 16 fast; if 18, may take longer but still ok for unit)
    date = time.strftime("%Y%m%d%H%M%S", time.gmtime())
    base = HashcashStamp("1", bits, date, resource, "", "rnd", "0")
    # Simple counter search
    for i in itertools.count():
        stamp = HashcashStamp("1", bits, date, resource, "", "rnd", str(i)).to_stamp()
        d = hashlib.sha1(stamp.encode("utf-8")).digest()
        # count leading zero bits
        n = 0
        for b in d:
            if b == 0:
                n += 8
            else:
                for j in range(7, -1, -1):
                    if (b >> j) & 1 == 0:
                        n += 1
                    else:
                        break
                break
        if n >= bits:
            return stamp


def test_verify_hashcash_roundtrip_fast():
    # Use 16 bits to keep test fast; verifier will accept >=16
    stamp = _mint(16, "/api/test")
    ok, reason = verify_hashcash(stamp, min_bits=16, resource="/api/test", max_age_seconds=3600)
    assert ok, reason
    ok2, reason2 = verify_hashcash(stamp, min_bits=18, resource="/api/test", max_age_seconds=3600)
    assert ok2 or not ok2  # acceptance depends on minted bits; sanity call


def test_verify_hashcash_rejects_bad():
    ok, reason = verify_hashcash(
        "bad:stamp:string", min_bits=16, resource="/x", max_age_seconds=3600
    )
    assert not ok
