"""Reverse proxy helpers for Omada ACS traffic."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from http import HTTPStatus
import http.client
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import os
from pathlib import Path
import ssl
import sys
from urllib.parse import urlsplit

from omada_saml_oidc.config import BridgeConfig, load_config


def rewrite_url(value: str, *, upstream_bases: Sequence[str], public_base: str) -> str:
    """Rewrite an upstream absolute URL to the public base URL."""

    for upstream_base in upstream_bases:
        if value.startswith(upstream_base):
            return public_base + value[len(upstream_base) :]
    return value


def rewrite_cookie_domain(value: str, *, upstream_hosts: Sequence[str], public_host: str) -> str:
    """Rewrite the cookie domain so the browser stores it for the public host."""

    for upstream_host in upstream_hosts:
        value = value.replace(f"Domain={upstream_host}", f"Domain={public_host}")
    return value


def rewrite_response_body(
    value: bytes, *, upstream_bases: Sequence[str], public_base: str
) -> bytes:
    """Rewrite absolute upstream URLs embedded in an ACS response body."""

    for upstream_base in upstream_bases:
        value = value.replace(upstream_base.encode("utf-8"), public_base.encode("utf-8"))
    return value


@dataclass(slots=True)
class ProxyState:
    """Hold the immutable configuration for the ACS proxy handler."""

    config: BridgeConfig
    ssl_context: ssl.SSLContext


def build_proxy_handler(state: ProxyState) -> type[BaseHTTPRequestHandler]:
    """Create a request handler class bound to ACS proxy state."""

    class ProxyHandler(BaseHTTPRequestHandler):
        """Proxy browser ACS traffic to the configured Omada upstreams."""

        server_version = "omada-saml-acs-proxy/1.0"

        def do_GET(self) -> None:
            """Serve health checks and proxy GET requests."""

            if self.path == "/healthz":
                self.send_response(HTTPStatus.OK)
                self.end_headers()
                self.wfile.write(b"ok")
                return
            self._proxy()

        def do_POST(self) -> None:
            """Proxy ACS POST submissions to Omada."""

            self._proxy()

        def _proxy(self) -> None:
            """Forward the current request through the upstream failover list."""

            body = self.rfile.read(int(self.headers.get("Content-Length", "0")))
            upstream_bases = [upstream.base_url for upstream in state.config.omada_upstreams]
            upstream_hosts = [
                urlsplit(upstream.base_url).hostname or ""
                for upstream in state.config.omada_upstreams
            ]
            last_error: Exception | None = None
            for upstream in state.config.omada_upstreams:
                try:
                    response = self._request_upstream(upstream.base_url, body)
                    if response[0] < 500:
                        self._send_upstream_response(
                            response, upstream_bases=upstream_bases, upstream_hosts=upstream_hosts
                        )
                        return
                    last_error = RuntimeError(f"{upstream.base_url} returned {response[0]}")
                except Exception as exc:
                    last_error = exc
            self.send_response(HTTPStatus.BAD_GATEWAY)
            self.end_headers()
            message = f"All Omada upstreams failed: {last_error}".encode()
            self.wfile.write(message)

        def _request_upstream(
            self, upstream_base: str, body: bytes
        ) -> tuple[int, str, list[tuple[str, str]], bytes]:
            """Send the proxied request to one Omada upstream."""

            upstream = urlsplit(upstream_base)
            if upstream.hostname is None:
                raise ValueError(f"upstream has no hostname: {upstream_base}")
            port = upstream.port or (443 if upstream.scheme == "https" else 80)
            if upstream.scheme == "https":
                conn: http.client.HTTPConnection = http.client.HTTPSConnection(
                    upstream.hostname,
                    port,
                    timeout=30,
                    context=state.ssl_context,
                )
            else:
                conn = http.client.HTTPConnection(upstream.hostname, port, timeout=30)
            headers: dict[str, str] = {}
            for key in (
                "Accept",
                "Accept-Language",
                "Content-Type",
                "Cookie",
                "Origin",
                "Referer",
                "User-Agent",
            ):
                value = self.headers.get(key)
                if value:
                    headers[key] = value
            headers["Host"] = urlsplit(state.config.omada_public_base_url).netloc
            headers["X-Forwarded-Host"] = urlsplit(state.config.omada_public_base_url).netloc
            headers["X-Forwarded-Proto"] = urlsplit(state.config.omada_public_base_url).scheme
            headers["X-Forwarded-Port"] = "443"
            headers["X-Forwarded-For"] = self.client_address[0]
            if body:
                headers["Content-Length"] = str(len(body))
            try:
                conn.request(self.command, self.path, body=body, headers=headers)
                response = conn.getresponse()
                return response.status, response.reason, response.getheaders(), response.read()
            finally:
                conn.close()

        def _send_upstream_response(
            self,
            response: tuple[int, str, list[tuple[str, str]], bytes],
            *,
            upstream_bases: Sequence[str],
            upstream_hosts: Sequence[str],
        ) -> None:
            """Return a rewritten upstream response to the browser."""

            status, reason, headers, body = response
            self.send_response(status, reason)
            public_host = urlsplit(state.config.omada_public_base_url).hostname or ""
            public_base = state.config.omada_public_base_url
            for key, value in headers:
                lower = key.lower()
                if lower in {"connection", "content-length", "transfer-encoding"}:
                    continue
                if lower == "location":
                    value = rewrite_url(
                        value, upstream_bases=upstream_bases, public_base=public_base
                    )
                elif lower == "set-cookie":
                    value = rewrite_cookie_domain(
                        value, upstream_hosts=upstream_hosts, public_host=public_host
                    )
                self.send_header(key, value)
            body = rewrite_response_body(
                body, upstream_bases=upstream_bases, public_base=public_base
            )
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, fmt: str, *args: object) -> None:
            """Write access logs to stdout."""

            print(f"{self.address_string()} - {fmt % args}", flush=True)

    return ProxyHandler


def run_proxy(config: BridgeConfig) -> None:
    """Run the ACS proxy HTTP server until interrupted."""

    handler = build_proxy_handler(
        ProxyState(config=config, ssl_context=ssl._create_unverified_context())
    )
    ThreadingHTTPServer(("127.0.0.1", config.internal_proxy_port), handler).serve_forever()


def main(argv: Sequence[str] | None = None) -> int:
    """Launch the ACS proxy from a config file."""

    _ = argv
    config_path = Path(
        os.environ.get("OMADA_BRIDGE_CONFIG", "/tmp/omada-saml-oidc/config/bridge.yaml")
    )
    config = load_config(config_path)
    run_proxy(config)
    return 0


if __name__ == "__main__":
    sys.exit(main())
