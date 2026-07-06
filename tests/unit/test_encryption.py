"""GMNAPEncryption round-trips (R51 — maintainer ruling: keep + repair).

The module was 'broken' only by an undeclared dependency: the crypto itself
is sound. `cryptography` is optional (requirements-dev); these tests skip
cleanly where it's absent and prove AES-256 + RSA round-trips where present.
"""

import pathlib

import pytest

pytest.importorskip("cryptography", reason="optional dep (requirements-dev)")

from src.core.encryption import GMNAPEncryption  # noqa: E402


@pytest.fixture()
def enc(tmp_path):
    return GMNAPEncryption(config_dir=tmp_path)


@pytest.mark.timeout(30)
def test_aes_roundtrip_str_bytes_dict(enc):
    assert (
        enc.decrypt_data(enc.encrypt_data("secret — Erdős")).decode()
        == "secret — Erdős"
    )
    assert enc.decrypt_data(enc.encrypt_data(b"\x00\x01bytes")) == b"\x00\x01bytes"
    ct = enc.encrypt_data({"k": "v", "n": 1})
    assert b'"k"' in enc.decrypt_data(ct)


@pytest.mark.timeout(30)
def test_rsa_roundtrip(enc):
    assert (
        enc.decrypt_with_rsa(enc.encrypt_with_rsa("rsa payload")).decode()
        == "rsa payload"
    )


@pytest.mark.timeout(30)
def test_ciphertext_not_plaintext(enc):
    ct = enc.encrypt_data("visible-marker-string")
    assert "visible-marker-string" not in ct


@pytest.mark.timeout(30)
def test_keys_persist_across_instances(tmp_path):
    a = GMNAPEncryption(config_dir=tmp_path)
    ct = a.encrypt_data("persistent")
    b = GMNAPEncryption(config_dir=tmp_path)  # same key material on disk
    assert b.decrypt_data(ct).decode() == "persistent"
