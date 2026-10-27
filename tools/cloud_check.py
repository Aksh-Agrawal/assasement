"""Read-only cloud connection check. Never prints endpoints or credentials."""

import socket
from urllib.parse import urlsplit

import httpx

from app.api.transport import create_client, failure_state, json_object
from app.auth.credentials import CredentialStore
from app.config import AppConfig


def check(config: AppConfig, *, transport=None) -> dict[str, str]:
    result = {"API configured": "YES" if config.api_base_url else "NO"}
    if not config.api_base_url:
        return {**result, "Cloud readiness": "WAITING_FOR_API_URL"}
    url = urlsplit(config.api_base_url)
    try:
        if transport is None:
            socket.getaddrinfo(url.hostname, url.port or (443 if url.scheme == "https" else 80))
        result["DNS resolution"] = "OK"
    except OSError:
        return {**result, "DNS resolution": "FAILED", "Cloud readiness": "OFFLINE"}
    credential = CredentialStore(config.credential_path).load_safe()
    result["Device auth state"] = "PAIRED" if credential else "NOT_PAIRED"
    try:
        with create_client(
            config.api_base_url, auth_token=credential.token if credential else None,
            connect_timeout=config.sync_connect_timeout, read_timeout=config.sync_read_timeout,
            transport=transport,
        ) as client:
            health = client.get("/health")
            health.raise_for_status()
            json_object(health)
            result["HTTPS connection"] = "VERIFIED" if url.scheme == "https" else "HTTP_DEVELOPMENT"
            result["Health endpoint"] = "OK"
            if credential:
                response = client.get("/api/v1/content/catalog")
                response.raise_for_status()
                from app.content.catalog import ContentCatalog

                ContentCatalog.from_dict(json_object(response))
                result["Catalogue accessibility"] = "OK"
            else:
                result["Catalogue accessibility"] = "PAIRING_REQUIRED"
        result["Cloud readiness"] = "READY" if credential else "PAIRING_REQUIRED"
    except (httpx.HTTPError, ValueError, TypeError, KeyError) as error:
        result["Cloud readiness"] = failure_state(error).value
    return result


def main() -> int:
    try:
        result = check(AppConfig())
    except ValueError:
        result = {"API configured": "INVALID", "Cloud readiness": "INVALID_CONFIGURATION"}
    for key, value in result.items():
        print(f"{key}: {value}")
    return 0 if result["Cloud readiness"] in {"WAITING_FOR_API_URL", "READY", "PAIRING_REQUIRED"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
