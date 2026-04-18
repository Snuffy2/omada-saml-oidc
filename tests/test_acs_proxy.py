"""Tests for ACS proxy rewrite helpers."""

from __future__ import annotations

from omada_saml_oidc.acs_proxy import rewrite_cookie_domain, rewrite_response_body, rewrite_url


def test_rewrite_url_maps_upstream_to_public_base() -> None:
    """Rewrite absolute upstream URLs back to the public hostname."""

    assert (
        rewrite_url(
            "https://10.0.0.1:18043/sso/saml/login",
            upstream_bases=("https://10.0.0.1:18043", "https://10.0.0.2:18043"),
            public_base="https://omada.example",
        )
        == "https://omada.example/sso/saml/login"
    )


def test_rewrite_cookie_domain_changes_upstream_host_to_public_host() -> None:
    """Rewrite a Set-Cookie domain for the browser-facing hostname."""

    assert (
        rewrite_cookie_domain(
            "session=abc; Domain=10.0.0.1; Path=/; Secure",
            upstream_hosts=("10.0.0.1", "10.0.0.2"),
            public_host="omada.example",
        )
        == "session=abc; Domain=omada.example; Path=/; Secure"
    )


def test_rewrite_response_body_replaces_all_upstream_bases() -> None:
    """Rewrite embedded upstream URLs in response bodies."""

    body = b"redirect https://10.0.0.1:18043/path and https://10.0.0.2:18043/path"
    rewritten = rewrite_response_body(
        body,
        upstream_bases=("https://10.0.0.1:18043", "https://10.0.0.2:18043"),
        public_base="https://omada.example",
    )

    assert rewritten == b"redirect https://omada.example/path and https://omada.example/path"
