"""Render SATOSA configuration files for the bridge runtime."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape

import yaml

from omada_saml_oidc.certs import CertificateBundle
from omada_saml_oidc.config import BridgeConfig


def render_internal_attributes() -> str:
    """Render SATOSA internal attribute mappings.

    Returns:
        YAML text mapping OIDC claims to SATOSA internal attributes and SAML
        attributes required by Omada.
    """

    payload: dict[str, Any] = {
        "attributes": {
            "subject": {"openid": ["sub"], "saml": ["uid"]},
            "username": {"openid": ["preferred_username", "username"], "saml": ["username"]},
            "mail": {
                "openid": ["email"],
                "saml": [
                    "email",
                    "emailAddress",
                    "mail",
                    "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress",
                ],
            },
            "name": {
                "openid": ["name"],
                "saml": [
                    "cn",
                    "name",
                    "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/name",
                ],
            },
            "givenname": {
                "openid": ["given_name"],
                "saml": [
                    "givenName",
                    "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/givenname",
                ],
            },
            "surname": {
                "openid": ["family_name"],
                "saml": [
                    "sn",
                    "surname",
                    "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/surname",
                ],
            },
            "groups": {"openid": ["groups"], "saml": ["groups"]},
            "resource_attribute": {"saml": ["resource_attribute"]},
            "omada_attribute": {"saml": ["omada_attribute"]},
            "usergroup": {"saml": ["usergroup"]},
            "usergroup_name": {"saml": ["usergroup_name"]},
        }
    }
    return yaml.safe_dump(payload, sort_keys=False)


def render_proxy_conf(config: BridgeConfig) -> str:
    """Render the main SATOSA proxy config.

    Args:
        config: Validated bridge config.

    Returns:
        YAML text for SATOSA's ``proxy_conf.yaml``.
    """

    payload: dict[str, Any] = {
        "BASE": config.public_base_url,
        "COOKIE_STATE_NAME": "SATOSA_STATE",
        "CONTEXT_STATE_DELETE": "yes",
        "cookies_samesite_compat": [["SATOSA_STATE", "SATOSA_STATE_LEGACY"]],
        "INTERNAL_ATTRIBUTES": str(config.satosa_internal_attributes_path),
        "BACKEND_MODULES": [str(config.satosa_backend_path)],
        "FRONTEND_MODULES": [str(config.satosa_frontend_path)],
        "MICRO_SERVICES": [str(config.satosa_microservice_path)],
        "LOGGING": {
            "version": 1,
            "formatters": {
                "simple": {
                    "format": "[%(asctime)s] [%(levelname)s] [%(name)s.%(funcName)s] %(message)s"
                }
            },
            "handlers": {
                "stdout": {
                    "class": "logging.StreamHandler",
                    "stream": "ext://sys.stdout",
                    "level": "INFO",
                    "formatter": "simple",
                }
            },
            "loggers": {
                "satosa": {"level": "INFO"},
                "saml2": {"level": "INFO"},
                "oic": {"level": "INFO"},
            },
            "root": {"level": "INFO", "handlers": ["stdout"]},
        },
    }
    return yaml.safe_dump(payload, sort_keys=False)


def render_backend(config: BridgeConfig) -> str:
    """Render the SATOSA OIDC backend config.

    Args:
        config: Validated bridge config.

    Returns:
        YAML text for SATOSA's OIDC backend module.
    """

    scopes = ", ".join(config.oidc_scopes.split())
    payload = (
        "module: omada_saml_oidc.satosa_plugins.backend.PrefixedCallbackOpenIDConnectBackend\n"
        f"name: {config.oidc_backend_name}\n"
        "config:\n"
        "  provider_metadata:\n"
        f"    issuer: {config.oidc_provider_issuer}\n"
        "  client:\n"
        "    verify_ssl: yes\n"
        "    auth_req_params:\n"
        "      response_type: code\n"
        f"      scope: [{scopes}]\n"
        "    client_metadata:\n"
        f"      client_id: {config.oidc_client_id}\n"
        f"      client_secret: {config.oidc_client_secret}\n"
        f"      redirect_uris: [{config.oidc_redirect_uri}]\n"
        "      token_endpoint_auth_method: client_secret_basic\n"
        "      subject_type: public\n"
        "    userinfo_request_method: GET\n"
    )
    return payload


def render_frontend(config: BridgeConfig, certs: CertificateBundle) -> str:
    """Render the SATOSA SAML frontend config.

    Args:
        config: Validated bridge config.
        certs: Persisted SAML signing cert/key paths.

    Returns:
        YAML text for SATOSA's SAML IdP frontend module.
    """

    payload: dict[str, Any] = {
        "module": "omada_saml_oidc.satosa_plugins.frontend.OmadaSAMLFrontend",
        "name": "Saml2IDP",
        "config": {
            "endpoints": {
                "single_sign_on_service": {
                    "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST": "sso/post",
                    "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect": "sso/redirect",
                }
            },
            "entityid_endpoint": True,
            "enable_metadata_reload": False,
            "idp_config": {
                "organization": {
                    "display_name": "Omada SAML to OIDC Bridge",
                    "name": "Omada SAML to OIDC Bridge",
                    "url": config.public_base_url,
                },
                "contact_person": [
                    {"contact_type": "technical", "email_address": "mailto:admin@example.invalid"}
                ],
                "key_file": str(certs.key_path),
                "cert_file": str(certs.cert_path),
                "metadata": {"local": [str(config.satosa_metadata_path)]},
                "entityid": "<base_url>/<name>/proxy.xml",
                "accepted_time_diff": 120,
                "service": {
                    "idp": {
                        "endpoints": {"single_sign_on_service": []},
                        "name": "Omada SAML to OIDC Bridge",
                        "name_id_format": [
                            "urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress",
                            "urn:oasis:names:tc:SAML:2.0:nameid-format:persistent",
                            "urn:oasis:names:tc:SAML:1.1:nameid-format:unspecified",
                        ],
                        "policy": {
                            "default": {
                                "attribute_restrictions": None,
                                "fail_on_missing_requested": False,
                                "lifetime": {"minutes": 15},
                                "name_form": "urn:oasis:names:tc:SAML:2.0:attrname-format:basic",
                                "sign_response": True,
                                "sign_assertion": True,
                                "encrypt_assertion": False,
                                "encrypted_advice_attributes": False,
                            }
                        },
                    }
                },
            },
        },
    }
    return yaml.safe_dump(payload, sort_keys=False)


def render_microservice(config: BridgeConfig) -> str:
    """Render the Omada synthetic attribute microservice.

    Args:
        config: Validated bridge config.

    Returns:
        YAML text for SATOSA's synthetic attribute microservice.
    """

    payload: dict[str, Any] = {
        "module": "satosa.micro_services.attribute_generation.AddSyntheticAttributes",
        "name": "OmadaAttributes",
        "config": {
            "synthetic_attributes": {
                "default": {
                    "default": {
                        "resource_attribute": config.omada_resource_id,
                        "omada_attribute": config.omada_id,
                        "usergroup": config.usergroup_template,
                        "usergroup_name": config.usergroup_template,
                    }
                }
            }
        },
    }
    return yaml.safe_dump(payload, sort_keys=False)


def render_metadata(config: BridgeConfig) -> str:
    """Render Omada SP metadata for all configured upstream entity IDs.

    Args:
        config: Validated bridge config.

    Returns:
        XML metadata containing one ``EntityDescriptor`` per upstream.
    """

    entities = "\n".join(
        _render_entity(config, upstream.sp_entity_id) for upstream in config.omada_upstreams
    )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        + (
            '<md:EntitiesDescriptor xmlns:md="urn:oasis:names:tc:SAML:2.0:metadata" '
            'Name="OmadaControllers">\n'
        )
        + f"{entities}\n"
        + "</md:EntitiesDescriptor>\n"
    )


def build_satosa_artifacts(config: BridgeConfig, certs: CertificateBundle) -> dict[Path, str]:
    """Build all generated SATOSA text artifacts.

    Args:
        config: Validated bridge config.
        certs: Persisted SAML signing cert/key paths.

    Returns:
        Mapping of destination file paths to text content.
    """

    return {
        config.satosa_config_path: render_proxy_conf(config),
        config.satosa_internal_attributes_path: render_internal_attributes(),
        config.satosa_backend_path: render_backend(config),
        config.satosa_frontend_path: render_frontend(config, certs),
        config.satosa_microservice_path: render_microservice(config),
        config.satosa_metadata_path: render_metadata(config),
    }


def _render_entity(config: BridgeConfig, entity_id: str) -> str:
    """Render one Omada SP entity descriptor.

    Args:
        config: Validated bridge config.
        entity_id: Omada SAML SP entity ID.

    Returns:
        XML fragment for one entity.
    """

    return f"""  <md:EntityDescriptor entityID="{escape(entity_id)}">
    <md:SPSSODescriptor
        protocolSupportEnumeration="urn:oasis:names:tc:SAML:2.0:protocol"
        AuthnRequestsSigned="false"
        WantAssertionsSigned="false">
      <md:NameIDFormat>urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress</md:NameIDFormat>
      <md:AssertionConsumerService
          Binding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST"
          Location="{escape(config.acs_url)}"
          index="0"
          isDefault="true"/>
      <md:AttributeConsumingService index="0">
        <md:ServiceName xml:lang="en">AttributeContract</md:ServiceName>
        <md:RequestedAttribute
            Name="resource_attribute"
            NameFormat="urn:oasis:names:tc:SAML:2.0:attrname-format:basic"/>
        <md:RequestedAttribute
            Name="omada_attribute"
            NameFormat="urn:oasis:names:tc:SAML:2.0:attrname-format:basic"/>
                <md:RequestedAttribute
                        Name="username"
                        NameFormat="urn:oasis:names:tc:SAML:2.0:attrname-format:basic"/>
                <md:RequestedAttribute
                        Name="usergroup_name"
                        NameFormat="urn:oasis:names:tc:SAML:2.0:attrname-format:basic"/>
      </md:AttributeConsumingService>
    </md:SPSSODescriptor>
  </md:EntityDescriptor>"""
