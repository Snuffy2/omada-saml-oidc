"""Prepare runtime artifacts and supervise all bridge child services."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
import os
from pathlib import Path
import signal
import subprocess
import sys
from urllib.parse import urlsplit

import yaml

from omada_saml_oidc.certs import CertificateBundle, ensure_self_signed_certificate
from omada_saml_oidc.config import BridgeConfig, ConfigError
from omada_saml_oidc.satosa_config import build_satosa_artifacts
from omada_saml_oidc.secrets import ensure_persisted_secret


@dataclass(frozen=True, slots=True)
class PreparedRuntime:
    """Describe generated runtime artifacts and child commands."""

    secret_path: Path
    cert_path: Path
    key_path: Path
    bridge_config_path: Path
    satosa_config_path: Path
    launcher_command: tuple[str, ...]
    proxy_command: tuple[str, ...]
    router_command: tuple[str, ...]
    satosa_command: tuple[str, ...]


def prepare_runtime(config: BridgeConfig) -> PreparedRuntime:
    """Write generated config, secrets, and certificates for the container.

    Args:
        config: Validated bridge config.

    Returns:
        Runtime file paths and child process commands.
    """

    ensure_persisted_secret(
        config.state_secret_path,
        provided=config.satosa_state_encryption_key,
    )
    certs = ensure_self_signed_certificate(
        cert_path=config.frontend_cert_path,
        key_path=config.frontend_key_path,
        common_name=_hostname(config.public_base_url),
        subject_alt_names=(_hostname(config.public_base_url), "localhost"),
    )

    config.config_dir.mkdir(parents=True, exist_ok=True)
    config.bridge_config_path.write_text(
        yaml.safe_dump(config.to_mapping(include_secrets=True), sort_keys=False)
    )
    os.chmod(config.bridge_config_path, 0o600)

    artifacts = build_satosa_artifacts(
        config, CertificateBundle(cert_path=certs.cert_path, key_path=certs.key_path)
    )
    for path, content in artifacts.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        if path == config.satosa_backend_path:
            os.chmod(path, 0o600)

    return PreparedRuntime(
        secret_path=config.state_secret_path,
        cert_path=config.frontend_cert_path,
        key_path=config.frontend_key_path,
        bridge_config_path=config.bridge_config_path,
        satosa_config_path=config.satosa_config_path,
        launcher_command=(sys.executable, "-m", "omada_saml_oidc.launcher"),
        proxy_command=(sys.executable, "-m", "omada_saml_oidc.acs_proxy"),
        router_command=(sys.executable, "-m", "omada_saml_oidc.router"),
        satosa_command=(
            sys.executable,
            "-m",
            "gunicorn",
            "--bind",
            f"127.0.0.1:{config.internal_satosa_port}",
            "--workers",
            str(config.satosa_workers),
            "--access-logfile",
            "-",
            "--error-logfile",
            "-",
            "--forwarded-allow-ips=*",
            "satosa.wsgi:app",
        ),
    )


def run_supervisor(config: BridgeConfig) -> int:
    """Run and monitor all bridge child processes.

    Args:
        config: Validated bridge config.

    Returns:
        The supervisor exit code.
    """

    runtime = prepare_runtime(config)
    child_env = os.environ.copy()
    child_env.update(
        {
            "OMADA_BRIDGE_CONFIG": str(runtime.bridge_config_path),
            "SATOSA_CONFIG": str(runtime.satosa_config_path),
            "SATOSA_STATE_ENCRYPTION_KEY": runtime.secret_path.read_text().strip(),
        }
    )
    processes = [
        subprocess.Popen(runtime.launcher_command, env=child_env),
        subprocess.Popen(runtime.proxy_command, env=child_env),
        subprocess.Popen(runtime.satosa_command, env=child_env),
        subprocess.Popen(runtime.router_command, env=child_env),
    ]

    def terminate(*_args: object) -> None:
        """Terminate every running child process.

        Args:
            *_args: Signal handler arguments, ignored.
        """

        for child in processes:
            if child.poll() is None:
                child.terminate()

    signal.signal(signal.SIGTERM, terminate)
    signal.signal(signal.SIGINT, terminate)

    exit_code = 0
    try:
        while True:
            for child in processes:
                result = child.poll()
                if result is not None:
                    exit_code = result
                    terminate()
                    return exit_code
            signal.pause()
    finally:
        terminate()
        for child in processes:
            if child.poll() is None:
                child.wait(timeout=10)


def main(argv: Sequence[str] | None = None) -> int:
    """Load environment configuration and run the bridge supervisor.

    Args:
        argv: Unused command-line arguments.

    Returns:
        Process exit code.
    """

    _ = argv
    try:
        config = BridgeConfig.from_env()
    except ConfigError as exc:
        print(f"configuration error: {exc}", file=sys.stderr)
        return 2
    return run_supervisor(config)


def _hostname(url: str) -> str:
    """Extract a hostname from an absolute URL.

    Args:
        url: Absolute URL.

    Returns:
        Hostname portion of the URL.

    Raises:
        ConfigError: Raised when the URL has no hostname.
    """

    host = urlsplit(url).hostname
    if not host:
        raise ConfigError(f"URL has no hostname: {url}")
    return host


if __name__ == "__main__":
    sys.exit(main())
