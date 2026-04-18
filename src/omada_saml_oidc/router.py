"""Public HTTP router for the single-container bridge."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from http import HTTPStatus
import http.client
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import os
from pathlib import Path
import sys
from urllib.parse import urlsplit

from omada_saml_oidc.config import BridgeConfig, load_config


@dataclass(frozen=True, slots=True)
class PublicRoute:
    """Describe one public route and its local target."""

    target_port: int
    target_name: str


def resolve_public_route(host: str, path: str, config: BridgeConfig) -> str:
    """Resolve a browser-facing request to an internal service name.

    Args:
        host: Host header without port.
        path: Request path without query string.
        config: Validated bridge config.

    Returns:
        ``launcher``, ``acs_proxy``, ``satosa``, or ``not_found``.
    """

    bridge_host = urlsplit(config.public_base_url).hostname or ""
    omada_host = urlsplit(config.omada_public_base_url).hostname or ""
    if host == bridge_host and path == config.launch_path:
        return "launcher"
    if host == omada_host and path == config.acs_path:
        return "acs_proxy"
    if host == bridge_host:
        return "satosa"
    return "not_found"


def build_public_routes(config: BridgeConfig) -> dict[str, PublicRoute]:
    """Build the router's internal service table.

    Args:
        config: Validated bridge config.

    Returns:
        Mapping of route names to local target ports.
    """

    return {
        "launcher": PublicRoute(target_port=config.internal_launcher_port, target_name="launcher"),
        "acs_proxy": PublicRoute(target_port=config.internal_proxy_port, target_name="acs_proxy"),
        "satosa": PublicRoute(target_port=config.internal_satosa_port, target_name="satosa"),
    }


@dataclass(slots=True)
class RouterState:
    """Hold immutable state for public router handlers."""

    config: BridgeConfig


def build_router_handler(state: RouterState) -> type[BaseHTTPRequestHandler]:
    """Create a request handler class bound to router state.

    Args:
        state: Router configuration state.

    Returns:
        A ``BaseHTTPRequestHandler`` subclass.
    """

    class RouterHandler(BaseHTTPRequestHandler):
        """Route public HTTP requests to local bridge components."""

        server_version = "omada-saml-oidc/1.0"

        def do_GET(self) -> None:
            """Route a GET request or answer the container health check."""

            if urlsplit(self.path).path == "/healthz":
                self._send_health()
                return
            self._proxy()

        def do_POST(self) -> None:
            """Route a POST request to the selected internal component."""

            self._proxy()

        def _send_health(self) -> None:
            """Return aggregate health for launcher, ACS proxy, and SATOSA."""

            checks = (
                ("launcher", state.config.internal_launcher_port, "/healthz"),
                ("acs_proxy", state.config.internal_proxy_port, "/healthz"),
                ("satosa", state.config.internal_satosa_port, "/Saml2IDP/proxy.xml"),
            )
            failures: list[str] = []
            for name, port, path in checks:
                if not _check_local_http(port, path):
                    failures.append(name)
            if failures:
                self.send_response(HTTPStatus.SERVICE_UNAVAILABLE)
                self.end_headers()
                self.wfile.write(f"unhealthy: {', '.join(failures)}\n".encode())
                return
            self.send_response(HTTPStatus.OK)
            self.end_headers()
            self.wfile.write(b"ok\n")

        def _proxy(self) -> None:
            """Forward the current request to the matching local service."""

            host = self.headers.get("Host", "").split(":", 1)[0]
            path = urlsplit(self.path).path
            route_name = resolve_public_route(host, path, state.config)
            if route_name == "not_found":
                self.send_response(HTTPStatus.NOT_FOUND)
                self.end_headers()
                self.wfile.write(b"not found")
                return
            route = build_public_routes(state.config)[route_name]
            body = self.rfile.read(int(self.headers.get("Content-Length", "0")))
            connection = http.client.HTTPConnection("127.0.0.1", route.target_port, timeout=30)
            headers = {
                key: value for key, value in self.headers.items() if key.lower() != "connection"
            }
            try:
                connection.request(self.command, self.path, body=body, headers=headers)
                response = connection.getresponse()
                response_body = response.read()
                self.send_response(response.status, response.reason)
                for key, value in response.getheaders():
                    if key.lower() in {"connection", "content-length", "transfer-encoding"}:
                        continue
                    self.send_header(key, value)
                self.send_header("Content-Length", str(len(response_body)))
                self.end_headers()
                self.wfile.write(response_body)
            finally:
                connection.close()

        def log_message(self, fmt: str, *args: object) -> None:
            """Write access logs to stdout.

            Args:
                fmt: Standard ``BaseHTTPRequestHandler`` format string.
                *args: Values interpolated into ``fmt``.
            """

            print(f"{self.address_string()} - {fmt % args}", flush=True)

    return RouterHandler


def run_router(config: BridgeConfig) -> None:
    """Run the public router.

    Args:
        config: Validated bridge config.
    """

    handler = build_router_handler(RouterState(config=config))
    ThreadingHTTPServer(config.router_address, handler).serve_forever()


def main(argv: Sequence[str] | None = None) -> int:
    """Launch the public router from the generated runtime config.

    Args:
        argv: Unused command-line arguments.

    Returns:
        Process exit code.
    """

    _ = argv
    config_path = Path(
        os.environ.get("OMADA_BRIDGE_CONFIG", "/tmp/omada-saml-oidc/config/bridge.yaml")
    )
    run_router(load_config(config_path))
    return 0


def _check_local_http(port: int, path: str) -> bool:
    """Check a local HTTP endpoint.

    Args:
        port: Local TCP port.
        path: HTTP path to request.

    Returns:
        True when the endpoint returns a status below 500.
    """

    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
    try:
        connection.request("GET", path)
        return connection.getresponse().status < 500
    except OSError:
        return False
    finally:
        connection.close()


if __name__ == "__main__":
    sys.exit(main())
