"""Module entrypoint for ``python -m omada_saml_oidc``."""

from __future__ import annotations

import sys

from omada_saml_oidc.supervisor import main


def run() -> int:
    """Run the bridge supervisor entrypoint.

    Returns:
        Process exit code from the supervisor.
    """

    return main()


if __name__ == "__main__":
    sys.exit(run())
