"""Safe, bounded JSON diagnostics for ASGI request and error bodies."""

import json
import re
from typing import Any, Optional, Sequence

_REDACTED = "[REDACTED]"
_OMITTED = "[OMITTED]"
_DEFAULT_SENSITIVE_PARTS = (
    "password",
    "passwd",
    "secret",
    "token",
    "authorization",
    "cookie",
    "session",
    "credential",
    "private_key",
    "api_key",
    "access_key",
    "csrf",
    "otp",
    "phone",
    "mobile",
    "email",
    "national_code",
    "nationalcode",
    "verification_code",
    "signature",
    "signed_url",
    "refresh",
    "pin",
)
_MAX_NODES = 2048
_MAX_STRING_LENGTH = 1024


def is_json_content_type(content_type: str) -> bool:
    """Return whether a media type represents JSON content."""
    media_type = content_type.split(";", 1)[0].strip().casefold()
    subtype = media_type.rsplit("/", 1)[-1] if "/" in media_type else ""
    return media_type == "application/json" or (
        media_type.startswith("application/") and subtype.endswith("+json")
    )


def _normalize_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.casefold()).strip("_")


def is_sensitive_field(key: str, excluded_fields: Sequence[str]) -> bool:
    """Return whether a field name should be redacted in request diagnostics."""
    normalized_exclusions = frozenset(
        _normalize_key(name) for name in excluded_fields
    )
    return _is_sensitive(key, normalized_exclusions)


def _is_sensitive(key: str, excluded_fields: frozenset[str]) -> bool:
    if len(key) > 256:
        return True
    normalized = _normalize_key(key)
    return normalized in excluded_fields or any(
        part in normalized for part in _DEFAULT_SENSITIVE_PARTS
    )


def _reject_json_constant(value: str) -> None:
    """Reject JavaScript-style NaN and infinity values accepted by json.loads."""
    raise ValueError(f"Invalid JSON constant: {value}")


def safe_path(value: str, *, max_length: int = 256) -> str:
    """Bound and neutralize control characters in a URL path for log output."""
    bounded = value[:max_length]
    if bounded.isprintable():
        return bounded
    return "".join(
        character if character.isprintable() else "?" for character in bounded
    )


def sanitize_user_agent(value: str, *, max_length: int = 180) -> str:
    """Keep a bounded set of product/version tokens, dropping control text."""
    control_pattern = re.compile(r"[\x00-\x1f\x7f-\x9f]")
    product_pattern = re.compile(
        r"(?<![A-Za-z0-9])([A-Za-z][A-Za-z0-9_.-]{0,31}/[0-9][A-Za-z0-9_.-]{0,31})"
    )
    products = product_pattern.findall(
        control_pattern.sub(" ", str(value))[:2048]
    )
    return (" ".join(products[:6]) or "Unknown User Agent")[:max_length]


def _sanitize_json_value(
    value: Any,
    *,
    excluded_fields: frozenset[str],
    depth: int,
    max_depth: int,
    budget: list[int],
) -> Any:
    """Sanitize decoded JSON without traversing unbounded structures."""
    if budget[0] <= 0:
        return _OMITTED
    budget[0] -= 1

    if isinstance(value, dict):
        if depth > max_depth:
            return _OMITTED
        result = {}
        for key, child in value.items():
            if budget[0] <= 0:
                result["[remaining fields]"] = _OMITTED
                break
            safe_key = key[:128] if len(key) > 128 else key
            result[safe_key] = (
                _REDACTED
                if _is_sensitive(key, excluded_fields)
                else _sanitize_json_value(
                    child,
                    excluded_fields=excluded_fields,
                    depth=depth + 1,
                    max_depth=max_depth,
                    budget=budget,
                )
            )
        return result

    if isinstance(value, list):
        if depth > max_depth:
            return _OMITTED
        result = []
        for child in value:
            if budget[0] <= 0:
                result.append(_OMITTED)
                break
            result.append(
                _sanitize_json_value(
                    child,
                    excluded_fields=excluded_fields,
                    depth=depth + 1,
                    max_depth=max_depth,
                    budget=budget,
                )
            )
        return result

    if isinstance(value, str):
        return value[:_MAX_STRING_LENGTH]
    if value is None or isinstance(value, (bool, int, float)):
        return value
    return _OMITTED


def format_json_diagnostic(
    body: bytes,
    content_type: str,
    *,
    excluded_fields: Sequence[str],
    max_depth: int,
    max_output_bytes: int = 65_536,
) -> Optional[str]:
    """Return redacted JSON text or a safe marker; never return raw body text.

    Only ``application/json`` and ``+json`` media types are accepted. Callers
    must enforce the byte limit while streaming the ASGI message body.
    """
    if not body:
        return None
    if not is_json_content_type(content_type):
        return "<unsupported content type>"
    try:
        decoded = json.loads(
            body.decode("utf-8"),
            parse_constant=_reject_json_constant,
        )
        if not isinstance(decoded, (dict, list)):
            return "<unstructured JSON body>"
        normalized_exclusions = frozenset(
            _normalize_key(name) for name in excluded_fields
        )
        sanitized = _sanitize_json_value(
            decoded,
            excluded_fields=normalized_exclusions,
            depth=0,
            max_depth=max_depth,
            budget=[_MAX_NODES],
        )
        serialized = json.dumps(
            sanitized,
            ensure_ascii=True,
            separators=(",", ":"),
            allow_nan=False,
        )
        if len(serialized.encode("utf-8")) > max_output_bytes:
            return "<oversized diagnostic>"
        return serialized
    except (
        UnicodeDecodeError,
        json.JSONDecodeError,
        RecursionError,
        ValueError,
        TypeError,
    ):
        return "<invalid JSON body>"


__all__ = [
    "format_json_diagnostic",
    "is_json_content_type",
    "is_sensitive_field",
    "safe_path",
    "sanitize_user_agent",
]
