# Omada SAML to OIDC Bridge

Omada SAML to OIDC Bridge lets an Omada Controller accept OIDC login through
SATOSA plus a small amount of custom routing and rewrite code. The public
browser flow stays on OIDC, while the bridge turns that login into the SAML
traffic Omada expects.

Use this when you want:

- a public OIDC login for Omada
- SATOSA as the OIDC-to-SAML broker
- custom launch and ACS handling for Omada Controller
- a deployment that works with Pocket ID or Authelia as the OIDC provider

## How it works

1. The browser goes to the public Omada URL.
2. The Omada launch route sends the browser into SATOSA.
3. SATOSA authenticates the user through the configured OIDC provider.
4. The bridge posts the SAML response back to Omada.
5. The custom proxy layer rewrites public URLs so Omada keeps redirecting to the
   browser-facing hostname instead of an internal controller address.

## Required URL rules

These settings must be correct before the bridge will behave properly:

- `PUBLIC_BASE_URL` must be a public `https://` URL for the bridge itself.
- `OIDC_PROVIDER_ISSUER` must be the public `https://` issuer URL for Pocket ID
  or Authelia.
- `OMADA_PUBLIC_BASE_URL` must be the public `https://` URL users open for
  Omada.
- `OMADA_UPSTREAM_BASES` must contain internal controller IPs or DNS names plus
  port, such as `https://10.0.0.11:443,https://omada-node-2.internal:443`.

Do not point `OMADA_UPSTREAM_BASES` at the public Omada hostname. The bridge
uses those upstream values to reach the controller directly inside the network.

## What you need

- a public HTTPS hostname for the bridge
- a public HTTPS hostname for the OIDC provider
- one or more internal Omada controller endpoints
- Docker and Docker Compose
- either Pocket ID or Authelia

## Docker Compose

The compose example in `examples/docker-compose.yml` shows the bridge container.
Copy `omada-saml-oidc.env.example` to `omada-saml-oidc.env`, fill in the Omada and OIDC values, and keep that
file private. The compose example uses the image name you should publish to your
own registry:

```yaml
image: ghcr.io/snuffy2/omada-saml-oidc:latest
```

The example keeps all hostnames generic:

- `bridge.example.com` for the public bridge hostname
- `omada.example.com` for the public Omada hostname
- `auth.example.com` for Pocket ID or Authelia
- `controller-1.internal` for the private Omada controller node

The compose file defines a shared `omada` Docker network so the bridge and the
OIDC provider can talk to each other without exposing the controller upstreams
to the public internet.

## Pocket ID setup

Pocket ID works well when you want a light OIDC provider dedicated to this
deployment.

1. Create an OIDC client for the bridge.
2. Set `OIDC_PROVIDER_ISSUER` to the public Pocket ID issuer URL.
3. Point the browser-facing Omada hostname at the bridge launch hostname.
4. Keep the controller upstreams private and reachable only from the bridge
   network.

Use `examples/docker-compose.yml` as the starting point, then attach Pocket ID
to the same Docker network and point `OIDC_PROVIDER_ISSUER` at its public
issuer URL.

## Authelia setup

Authelia is the right fit when you already use it as your main identity layer.

1. Create an OIDC client for the bridge in Authelia.
2. Set `OIDC_PROVIDER_ISSUER` to the public Authelia issuer URL.
3. Keep the Authelia public URL on HTTPS.
4. Route the Omada hostname to the ACS handler and the launch hostname to the
   bridge.

Use the same compose file, then attach Authelia to the same Docker network and
point `OIDC_PROVIDER_ISSUER` at its public issuer URL.

## Traefik

Use `examples/traefik-pocket-id.yml` when Pocket ID is the OIDC provider, or
`examples/traefik-authelia.yml` when Authelia is the OIDC provider.

Both files show the same public flow:

- `omada.example.com/` redirects to the bridge launch path
- `bridge.example.com/launch/omada` goes to the bridge launcher
- `omada.example.com/sso/saml/login` goes to the bridge ACS handler
- the rest of the Omada hostname goes to the controller upstream
- `auth.example.com` goes to the OIDC provider

The public Omada hostname and the login hostname both stay on HTTPS.

## nginx

Use `examples/nginx-pocket-id.conf` for Pocket ID or
`examples/nginx-authelia.conf` for Authelia.

Both files show the same flow with nginx:

- redirect `/` to the bridge launch path
- `bridge.example.com/launch/omada` goes to the bridge launcher
- proxy `/sso/saml/login` to the bridge
- proxy the remaining Omada traffic to the controller upstream
- proxy the OIDC provider hostname to the IdP

Use nginx when you want the routing rules in one place and prefer explicit
server blocks over Traefik labels.

## Example files

- `.env.example`
- `examples/docker-compose.yml`
- `examples/traefik-pocket-id.yml`
- `examples/traefik-authelia.yml`
- `examples/nginx-pocket-id.conf`
- `examples/nginx-authelia.conf`

## License

MIT. See [`LICENSE`](LICENSE).
