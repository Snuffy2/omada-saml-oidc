"""Tests for SATOSA config generation."""

from __future__ import annotations

from pathlib import Path

import yaml

from omada_saml_oidc.certs import CertificateBundle
from omada_saml_oidc.config import BridgeConfig
from omada_saml_oidc.satosa_config import build_satosa_artifacts
from tests.test_config import valid_env


def test_build_satosa_artifacts_use_env_values_without_private_defaults(tmp_path: Path) -> None:
    """Render SATOSA artifacts from placeholder-safe env values."""

    config = BridgeConfig.from_env(valid_env(tmp_path))
    certs = CertificateBundle(
        cert_path=tmp_path / "frontend.crt", key_path=tmp_path / "frontend.key"
    )

    artifacts = build_satosa_artifacts(config, certs)

    assert config.satosa_config_path in artifacts
    assert config.satosa_internal_attributes_path in artifacts
    assert config.satosa_backend_path in artifacts
    assert config.satosa_frontend_path in artifacts
    assert config.satosa_microservice_path in artifacts
    assert config.satosa_metadata_path in artifacts

    proxy_conf = yaml.safe_load(artifacts[config.satosa_config_path])
    assert proxy_conf["BASE"] == "https://bridge.example.com"
    assert proxy_conf["INTERNAL_ATTRIBUTES"] == str(config.satosa_internal_attributes_path)

    backend = artifacts[config.satosa_backend_path]
    assert "issuer: https://auth.example.com" in backend
    assert "redirect_uris: [https://bridge.example.com/oidc]" in backend
    assert "client_secret: secret" in backend

    microservice = yaml.safe_load(artifacts[config.satosa_microservice_path])
    synthetic = microservice["config"]["synthetic_attributes"]["default"]["default"]
    assert synthetic["resource_attribute"] == "resource-id"
    assert synthetic["omada_attribute"] == "omada-id"

    metadata = artifacts[config.satosa_metadata_path]
    assert 'entityID="https://controller-1.internal:443/omada-id"' in metadata
    assert 'Location="https://omada.example.com/sso/saml/login"' in metadata
