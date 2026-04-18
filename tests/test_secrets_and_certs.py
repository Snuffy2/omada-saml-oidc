"""Tests for persisted secret and certificate generation."""

from __future__ import annotations

from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from omada_saml_oidc.certs import ensure_self_signed_certificate
from omada_saml_oidc.secrets import ensure_persisted_secret


def test_ensure_persisted_secret_keeps_stable_value(tmp_path: Path) -> None:
    """Create a secret once and reuse the same text on subsequent calls."""

    secret_path = tmp_path / "satosa_state_encryption_key"

    first = ensure_persisted_secret(secret_path)
    second = ensure_persisted_secret(secret_path)

    assert first == second
    assert secret_path.read_text().strip() == first
    assert len(first) >= 32


def test_ensure_self_signed_certificate_persists_cert_and_key(tmp_path: Path) -> None:
    """Generate a certificate bundle and keep it stable across reruns."""

    cert_path = tmp_path / "frontend.crt"
    key_path = tmp_path / "frontend.key"

    first = ensure_self_signed_certificate(
        cert_path=cert_path,
        key_path=key_path,
        common_name="satosa.example",
        subject_alt_names=("satosa.example", "localhost"),
    )
    second = ensure_self_signed_certificate(
        cert_path=cert_path,
        key_path=key_path,
        common_name="satosa.example",
        subject_alt_names=("satosa.example", "localhost"),
    )

    assert first == second
    assert cert_path.exists()
    assert key_path.exists()

    cert = x509.load_pem_x509_certificate(cert_path.read_bytes())
    subject = cert.subject.get_attributes_for_oid(x509.oid.NameOID.COMMON_NAME)[0].value
    assert subject == "satosa.example"
    san = cert.extensions.get_extension_for_class(x509.SubjectAlternativeName).value
    assert set(san.get_values_for_type(x509.DNSName)) == {"satosa.example", "localhost"}

    key = serialization.load_pem_private_key(key_path.read_bytes(), password=None)
    assert isinstance(key, rsa.RSAPrivateKey)
    assert key.key_size >= 2048
