"""Tests for the Omada SAML launch helper."""

from __future__ import annotations

import base64
import zlib

from omada_saml_oidc.config import UpstreamConfig
from omada_saml_oidc.launcher import build_saml_request, select_sp_entity_id


def test_build_saml_request_encodes_the_expected_xml() -> None:
    """Create a redirect-binding SAML AuthnRequest."""

    saml_request = build_saml_request(
        sp_entity_id="https://10.0.0.1:18043/entity",
        destination="https://bridge.example.com/oidc/sso/redirect",
        acs_url="https://omada.example/sso/saml/login",
        issue_instant="2026-04-17T12:00:00Z",
        request_id="_test-id",
    )

    xml = zlib.decompress(base64.b64decode(saml_request), wbits=-15).decode("utf-8")
    assert 'Destination="https://bridge.example.com/oidc/sso/redirect"' in xml
    assert 'AssertionConsumerServiceURL="https://omada.example/sso/saml/login"' in xml
    assert "<saml:Issuer>https://10.0.0.1:18043/entity</saml:Issuer>" in xml


def test_select_sp_entity_id_chooses_first_healthy_upstream() -> None:
    """Pick the first upstream that reports healthy."""

    upstreams = (
        UpstreamConfig(base_url="https://10.0.0.1:18043", sp_entity_id="first"),
        UpstreamConfig(base_url="https://10.0.0.2:18043", sp_entity_id="second"),
    )

    selected = select_sp_entity_id(
        upstreams,
        health_check=lambda base_url: base_url.endswith("10.0.0.2:18043"),
    )

    assert selected == "second"
