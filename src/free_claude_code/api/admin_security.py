
"""Admin security boundary: local access or password-protected remote access."""

import base64
import binascii
import hmac
import ipaddress
import os
from urllib.parse import urlsplit

from fastapi import HTTPException, Request


def _is_loopback_host(host: str | None) -> bool:
    if host is None:
        return False

    normalized = host.strip().strip("[]").lower()
    if normalized == "localhost":
        return True

    try:
        return ipaddress.ip_address(normalized).is_loopback
    except ValueError:
        return False


def _origin_is_local(origin: str | None) -> bool:
    if not origin:
        return True

    try:
        parsed = urlsplit(origin)
        _ = parsed.port
    except ValueError:
        return False

    return (
        parsed.scheme in {"http", "https"}
        and parsed.username is None
        and parsed.password is None
        and not parsed.path
        and not parsed.query
        and not parsed.fragment
        and _is_loopback_host(parsed.hostname)
    )


def _authority_is_local(authority: str | None) -> bool:
    if not authority:
        return False

    try:
        parsed = urlsplit(f"//{authority}")
        _ = parsed.port
    except ValueError:
        return False

    return (
        parsed.username is None
        and parsed.password is None
        and not parsed.path
        and not parsed.query
        and not parsed.fragment
        and _is_loopback_host(parsed.hostname)
    )


def _unauthorized() -> HTTPException:
    return HTTPException(
        status_code=401,
        detail="Admin authentication required",
        headers={"WWW-Authenticate": 'Basic realm="Free Claude Code Admin"'},
    )


def _valid_basic_auth(request: Request, expected_password: str) -> bool:
    authorization = request.headers.get("authorization", "")
    scheme, separator, encoded = authorization.partition(" ")

    if not separator or scheme.lower() != "basic" or not encoded:
        return False

    try:
        decoded = base64.b64decode(encoded, validate=True).decode("utf-8")
    except (binascii.Error, UnicodeDecodeError, ValueError):
        return False

    username, separator, password = decoded.partition(":")
    if not separator:
        return False

    return (
        hmac.compare_digest(username, "admin")
        and hmac.compare_digest(password, expected_password)
    )


def require_loopback_admin(request: Request) -> None:
    """Allow local loopback access or password-authenticated remote access."""

    client_host = request.client.host if request.client else None
    host_is_local = _authority_is_local(request.headers.get("host"))
    client_is_local = _is_loopback_host(client_host)

    # Preserve existing local development behavior.
    if client_is_local and host_is_local:
        if not _origin_is_local(request.headers.get("origin")):
            raise HTTPException(status_code=403, detail="Invalid Admin origin")
        return

    # Remote access must have a configured password.
    expected_password = os.environ.get("FCC_ADMIN_PASSWORD", "")
    if len(expected_password) < 16:
        raise HTTPException(
            status_code=503,
            detail="Remote Admin is disabled: configure FCC_ADMIN_PASSWORD "
            "with at least 16 characters",
        )

    # For browser requests, reject a cross-origin Origin header.
    origin = request.headers.get("origin")
    if origin:
        try:
            parsed_origin = urlsplit(origin)
            origin_host = parsed_origin.netloc.lower()
            request_host = (request.headers.get("host") or "").lower()
        except ValueError:
            raise HTTPException(status_code=403, detail="Invalid Admin origin") from None

        if (
            parsed_origin.scheme not in {"http", "https"}
            or parsed_origin.username is not None
            or parsed_origin.password is not None
            or origin_host != request_host
            or parsed_origin.path
            or parsed_origin.query
            or parsed_origin.fragment
        ):
            raise HTTPException(status_code=403, detail="Invalid Admin origin")

    if not _valid_basic_auth(request, expected_password):
        raise _unauthorized()
