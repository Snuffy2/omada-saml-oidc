"""Tests for public router route resolution."""

from __future__ import annotations

from pathlib import Path

from omada_saml_oidc.config import BridgeConfig
from omada_saml_oidc.router import build_public_routes, resolve_public_route
from tests.test_config import valid_env


def test_resolve_public_route_maps_public_hosts_to_internal_services(tmp_path: Path) -> None:
    """Route bridge and Omada hostnames to the correct internal service."""

    config = BridgeConfig.from_env(valid_env(tmp_path))

    assert resolve_public_route("bridge.example.com", "/launch/omada", config) == "launcher"
    assert resolve_public_route("bridge.example.com", "/Saml2IDP/proxy.xml", config) == "satosa"
    assert resolve_public_route("bridge.example.com", "/oidc/sso/redirect", config) == "satosa"
    assert resolve_public_route("omada.example.com", "/sso/saml/login", config) == "acs_proxy"
    assert resolve_public_route("omada.example.com", "/", config) == "not_found"


def test_build_public_routes_uses_internal_ports(tmp_path: Path) -> None:
    """Build route targets using private loopback service ports."""

    config = BridgeConfig.from_env(valid_env(tmp_path))
    routes = build_public_routes(config)

    assert routes["launcher"].target_port == config.internal_launcher_port
    assert routes["acs_proxy"].target_port == config.internal_proxy_port
    assert routes["satosa"].target_port == config.internal_satosa_port
