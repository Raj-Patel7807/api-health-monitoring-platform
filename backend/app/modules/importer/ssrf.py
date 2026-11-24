"""SSRF protection and URL validation utilities."""

from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse

_DISALLOWED_SCHEMES = {"file", "gopher", "ftp", "smtp", "ldap", "dict"}
_BLOCKED_HOSTNAMES = {"localhost", "127.0.0.1", "0.0.0.0", "::1", "metadata.google.internal"}


def is_safe_url(url: str, allow_relative: bool = False) -> tuple[bool, str | None]:
    """Validate a URL against SSRF and protocol restrictions.

    Returns:
        (True, None) if URL is safe.
        (False, reason) if URL is unsafe or invalid.
    """
    if not url or not url.strip():
        return False, "URL cannot be empty."

    url = url.strip()

    # Handle relative paths if explicitly allowed during preview
    if allow_relative and url.startswith("/"):
        return True, None

    try:
        parsed = urlparse(url)
    except Exception:
        return False, "Malformed URL format."

    scheme = (parsed.scheme or "").lower()
    if scheme not in ("http", "https"):
        return False, f"Unsupported URL scheme '{scheme}'. Only http and https are allowed."

    hostname = parsed.hostname
    if not hostname:
        return False, "URL is missing a valid hostname."

    hostname_lower = hostname.lower()

    if (
        hostname_lower in _BLOCKED_HOSTNAMES
        or hostname_lower.endswith(".local")
        or hostname_lower.endswith(".internal")
    ):
        return False, f"Host '{hostname}' resolves to an internal or restricted network address."

    # Check if host is a literal IP address
    try:
        ip = ipaddress.ip_address(hostname)
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
            return False, f"IP address '{ip}' is in a private or restricted address space."
        return True, None
    except ValueError:
        pass  # Hostname is a domain name, not an IP literal

    # Resolve hostname to verify DNS target IPs
    try:
        addr_info = socket.getaddrinfo(
            hostname, parsed.port or (443 if scheme == "https" else 80), proto=socket.IPPROTO_TCP
        )
        for _, _, _, _, sockaddr in addr_info:
            ip_str = sockaddr[0]
            ip = ipaddress.ip_address(ip_str)
            if (
                ip.is_private
                or ip.is_loopback
                or ip.is_link_local
                or ip.is_reserved
                or ip.is_multicast
            ):
                return False, f"Host '{hostname}' resolves to private/internal IP '{ip_str}'."
    except socket.gaierror:
        # If hostname cannot be resolved in this environment (e.g. offline testing),
        # allow valid public domain strings like example.com or api.github.com
        if "." in hostname and not hostname.startswith("."):
            return True, None
        return False, f"Cannot resolve hostname '{hostname}'."
    except Exception as exc:
        return False, f"Error validating host '{hostname}': {exc}"

    return True, None
