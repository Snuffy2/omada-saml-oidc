"""Tests for supervisor runtime preparation."""

from __future__ import annotations

from pathlib import Path

from omada_saml_oidc.config import BridgeConfig
from omada_saml_oidc.supervisor import prepare_runtime
from tests.test_config import valid_env


def test_prepare_runtime_writes_generated_runtime_files(tmp_path: Path) -> None:
    """Write persistent and runtime files required by child processes."""

    config = BridgeConfig.from_env(valid_env(tmp_path))

    runtime = prepare_runtime(config)

    assert runtime.secret_path.exists()
    assert runtime.cert_path.exists()
    assert runtime.key_path.exists()
    assert runtime.bridge_config_path.exists()
    assert runtime.satosa_config_path.exists()
    assert runtime.launcher_command == (
        "python",
        "-m",
        "omada_saml_oidc.launcher",
    ) or runtime.launcher_command[1:] == (
        "-m",
        "omada_saml_oidc.launcher",
    )


def test_prepare_runtime_persists_provided_state_secret(tmp_path: Path) -> None:
    """Persist a caller-provided SATOSA state encryption key on first run."""

    env = valid_env(tmp_path)
    env["SATOSA_STATE_ENCRYPTION_KEY"] = "provided-state-key"
    config = BridgeConfig.from_env(env)

    runtime = prepare_runtime(config)

    assert runtime.secret_path.read_text().strip() == "provided-state-key"
