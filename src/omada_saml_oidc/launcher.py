"""HTTP launcher that starts the Omada SAML flow."""

from __future__ import annotations

import base64
from collections.abc import Callable, Sequence
from dataclasses import dataclass
import datetime as dt
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import os
from pathlib import Path
import sys
from urllib.parse import urlencode, urlsplit
import uuid
from xml.sax.saxutils import escape
import zlib

from omada_saml_oidc.config import BridgeConfig, UpstreamConfig, load_config


def build_saml_request(
    *,
    sp_entity_id: str,
    destination: str,
    acs_url: str,
    issue_instant: str | None = None,
    request_id: str | None = None,
) -> str:
    """Build a base64-encoded raw-deflate SAML AuthnRequest."""

    request_id = request_id or "_" + uuid.uuid4().hex
    issue_instant = issue_instant or (
        dt.datetime.now(dt.UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    )
    xml = (
        f'<samlp:AuthnRequest xmlns:samlp="urn:oasis:names:tc:SAML:2.0:protocol" '
        f'xmlns:saml="urn:oasis:names:tc:SAML:2.0:assertion" ID="{request_id}" '
        f'Version="2.0" IssueInstant="{issue_instant}" '
        f'Destination="{escape(destination)}" '
        f'ProtocolBinding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST" '
        f'AssertionConsumerServiceURL="{escape(acs_url)}">'
        f"<saml:Issuer>{escape(sp_entity_id)}</saml:Issuer>"
        "</samlp:AuthnRequest>"
    )
    compressor = zlib.compressobj(wbits=-15)
    deflated = compressor.compress(xml.encode("utf-8")) + compressor.flush()
    return base64.b64encode(deflated).decode("ascii")


def select_sp_entity_id(
    upstreams: Sequence[UpstreamConfig],
    health_check: Callable[[str], bool],
) -> str:
    """Choose the first Omada SP entity ID whose upstream is healthy."""

    if not upstreams:
        raise ValueError("at least one upstream is required")
    for upstream in upstreams:
        if health_check(upstream.base_url):
            return upstream.sp_entity_id
    return upstreams[0].sp_entity_id


@dataclass(slots=True)
class LauncherHandlerState:
    """Hold the immutable state used by launcher HTTP handlers."""

    config: BridgeConfig
    health_check: Callable[[str], bool]


def build_launcher_handler(state: LauncherHandlerState) -> type[BaseHTTPRequestHandler]:
    """Create a request handler class bound to launcher state."""

    class LauncherHandler(BaseHTTPRequestHandler):
        """Handle the health and launch endpoints for the bridge."""

        server_version = "omada-saml-launcher/1.0"

        def do_GET(self) -> None:
            """Serve the health check or launch redirect."""

            path = urlsplit(self.path).path
            if path == "/healthz":
                self.send_response(HTTPStatus.OK)
                self.end_headers()
                self.wfile.write(b"ok\n")
                return
            if path != state.config.launch_path:
                self.send_response(HTTPStatus.NOT_FOUND)
                self.end_headers()
                self.wfile.write(b"not found\n")
                return

            sp_entity_id = select_sp_entity_id(state.config.omada_upstreams, state.health_check)
            saml_request = build_saml_request(
                sp_entity_id=sp_entity_id,
                destination=state.config.sso_redirect_url,
                acs_url=state.config.acs_url,
            )
            query = urlencode({"SAMLRequest": saml_request, "RelayState": state.config.relay_state})
            self.send_response(HTTPStatus.FOUND)
            self.send_header("Location", f"{state.config.sso_redirect_url}?{query}")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()

        def log_message(self, fmt: str, *args: object) -> None:
            """Write access logs to stdout."""

            print(f"{self.address_string()} - {fmt % args}", flush=True)

    return LauncherHandler


def run_launcher(config: BridgeConfig, health_check: Callable[[str], bool]) -> None:
    """Run the launcher HTTP server until interrupted."""

    handler = build_launcher_handler(LauncherHandlerState(config=config, health_check=health_check))
    ThreadingHTTPServer(("127.0.0.1", config.internal_launcher_port), handler).serve_forever()


def default_health_check(url: str) -> bool:
    """Return whether an upstream looks usable by probing its base URL."""

    import ssl
    import urllib.request

    req = urllib.request.Request(url + "/", method="HEAD")
    context = ssl._create_unverified_context()
    try:
        with urllib.request.urlopen(req, timeout=3.0, context=context) as response:
            return 200 <= int(response.status) < 500
    except Exception:
        return False


def main(argv: Sequence[str] | None = None) -> int:
    """Launch the Omada SAML helper service from a config file."""

    _ = argv
    config_path = Path(
        os.environ.get("OMADA_BRIDGE_CONFIG", "/tmp/omada-saml-oidc/config/bridge.yaml")
    )
    config = load_config(config_path)
    run_launcher(config, default_health_check)
    return 0


if __name__ == "__main__":
    sys.exit(main())
