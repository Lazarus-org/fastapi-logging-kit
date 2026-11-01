"""Public v1 configuration contract, independent of the host settings library.

Legacy flat keys remain supported by the legacy integration path. Structured request-
middleware settings are copied into each application. Python's logging registry and
logger/handler graph remain process-wide, as defined by stdlib logging; this contract
does not create isolated logging registries per app.
"""

from collections.abc import Mapping
from copy import deepcopy
from typing import Any

from fastapi_logging_kit.settings.components import (
    ComponentConfigurationError,
    validate_components,
)

PUBLIC_KEYS = frozenset({"ENABLED", "LOGGING", "COMPONENTS", "REQUEST_LOGGING"})
REQUEST_DEFAULTS: dict[str, Any] = {
    "ENABLED": True,
    "LOG_REQUEST_STARTED": False,
    "LOG_REQUEST_FINISHED": True,
    "LOG_EXCEPTIONS": True,
    "LOG_STREAMING_EVENTS": False,
    "LOG_SQL_QUERIES": False,
    "MAX_SQL_BYTES": 4096,
    "MAX_SQL_QUERIES": 100,
    "REQUEST_ID_HEADER": "X-Request-ID",
    "RESPONSE_ID_HEADER": "X-Request-ID",
    "MAX_REQUEST_ID_LENGTH": 80,
    "USER_AGENT_ENABLED": True,
    "QUERY_PARAMS_ENABLED": False,
    "REQUEST_BODY_ENABLED": False,
    "ERROR_RESPONSE_BODY_ENABLED": False,
    "EXCLUDED_PATHS": [],
    "EXCLUDED_PATH_PREFIXES": [],
    "EXCLUDED_FIELDS": [
        "password",
        "token",
        "access_token",
        "refresh_token",
        "authorization",
        "api_key",
        "secret",
    ],
    "EXCLUDED_FIELDS_BY_PATH": {},
    "MAX_QUERY_BYTES": 4096,
    "MAX_BODY_BYTES": 2048,
    "MAX_ERROR_RESPONSE_BYTES": 2048,
    "MAX_DIAGNOSTIC_DEPTH": 8,
    "TRUSTED_PROXIES": [],
}


def _string_sequence(value: Any, field: str) -> list[str]:
    if not isinstance(value, (tuple, list)) or any(
        not isinstance(v, str) or not v for v in value
    ):
        raise ComponentConfigurationError(f"{field} must be a list of nonempty strings")
    return list(value)


def compile_settings(config: Mapping[str, Any]) -> dict[str, Any]:
    """Normalize an explicit configuration without changing global loggers.

    Invalid settings fail before middleware or handlers are installed. No environment
    module is imported; developers own settings discovery.
    """
    # pylint: disable=too-many-branches,too-many-statements,unidiomatic-typecheck
    if not isinstance(config, Mapping):
        raise ComponentConfigurationError("FASTAPI_LOGGING must be a mapping")
    if any(not isinstance(key, str) for key in config):
        raise ComponentConfigurationError("FASTAPI_LOGGING keys must be strings")
    unknown = set(config) - PUBLIC_KEYS
    if unknown:
        raise ComponentConfigurationError(
            f"Unknown FASTAPI_LOGGING keys: {sorted(unknown)}"
        )
    enabled = config.get("ENABLED", True)
    if not isinstance(enabled, bool):
        raise ComponentConfigurationError("ENABLED must be boolean")

    logging_conf = config.get("LOGGING", {})
    if not isinstance(logging_conf, Mapping):
        raise ComponentConfigurationError("LOGGING must be a dictConfig mapping")
    if logging_conf:
        if logging_conf.get("version") != 1:
            raise ComponentConfigurationError("LOGGING.version must be 1")
        if logging_conf.get("incremental", False):
            raise ComponentConfigurationError("Incremental dictConfig is not supported")

    # Component definitions are validated before any global logging state is changed.
    components = config.get("COMPONENTS", {})
    validate_components(components)

    supplied_request = config.get("REQUEST_LOGGING", {})
    if not isinstance(supplied_request, Mapping):
        raise ComponentConfigurationError("REQUEST_LOGGING must be a mapping")
    unknown_request = set(supplied_request) - set(REQUEST_DEFAULTS)
    if unknown_request:
        raise ComponentConfigurationError(
            f"Unknown REQUEST_LOGGING keys: {sorted(unknown_request)}"
        )
    request = deepcopy(REQUEST_DEFAULTS)
    request.update(deepcopy(dict(supplied_request)))
    boolean_fields = (
        "ENABLED",
        "LOG_REQUEST_STARTED",
        "LOG_REQUEST_FINISHED",
        "LOG_EXCEPTIONS",
        "LOG_STREAMING_EVENTS",
        "LOG_SQL_QUERIES",
        "USER_AGENT_ENABLED",
        "QUERY_PARAMS_ENABLED",
        "REQUEST_BODY_ENABLED",
        "ERROR_RESPONSE_BODY_ENABLED",
    )
    for name in boolean_fields:
        if not isinstance(request[name], bool):
            raise ComponentConfigurationError(f"REQUEST_LOGGING.{name} must be boolean")
    for name in ("REQUEST_ID_HEADER", "RESPONSE_ID_HEADER"):
        value = request[name]
        if (
            not isinstance(value, str)
            or not value
            or not value.isascii()
            or any(not (char.isalnum() or char == "-") for char in value)
        ):
            raise ComponentConfigurationError(
                f"REQUEST_LOGGING.{name} must be an HTTP header name"
            )
    for name in (
        "MAX_QUERY_BYTES",
        "MAX_BODY_BYTES",
        "MAX_ERROR_RESPONSE_BYTES",
        "MAX_SQL_BYTES",
        "MAX_DIAGNOSTIC_DEPTH",
    ):
        minimum = 1 if name.endswith("DEPTH") else 0
        if name.endswith("DEPTH"):
            maximum = 16
        elif name == "MAX_SQL_BYTES":
            maximum = 1_048_576
        else:
            maximum = 65_536
        if type(request[name]) is not int or not minimum <= request[name] <= maximum:
            raise ComponentConfigurationError(
                f"REQUEST_LOGGING.{name} must be between {minimum} and {maximum}"
            )
    max_sql_queries = request["MAX_SQL_QUERIES"]
    if type(max_sql_queries) is not int or not 1 <= max_sql_queries <= 10_000:
        raise ComponentConfigurationError(
            "REQUEST_LOGGING.MAX_SQL_QUERIES must be between 1 and 10000"
        )
    request_id_length = request["MAX_REQUEST_ID_LENGTH"]
    if type(request_id_length) is not int or not 1 <= request_id_length <= 256:
        raise ComponentConfigurationError(
            "REQUEST_LOGGING.MAX_REQUEST_ID_LENGTH must be between 1 and 256"
        )
    for name in (
        "EXCLUDED_PATHS",
        "EXCLUDED_PATH_PREFIXES",
        "EXCLUDED_FIELDS",
        "TRUSTED_PROXIES",
    ):
        request[name] = _string_sequence(request[name], f"REQUEST_LOGGING.{name}")
    for name in ("EXCLUDED_PATHS", "EXCLUDED_PATH_PREFIXES"):
        if any(not p.startswith("/") for p in request[name]):
            raise ComponentConfigurationError(
                f"REQUEST_LOGGING.{name} requires absolute paths"
            )
    for proxy in request["TRUSTED_PROXIES"]:
        try:
            import ipaddress

            ipaddress.ip_network(proxy, strict=False)
        except ValueError as exc:
            raise ComponentConfigurationError(
                f"Invalid trusted proxy network: {proxy!r}"
            ) from exc
    by_path = request["EXCLUDED_FIELDS_BY_PATH"]
    if not isinstance(by_path, Mapping):
        raise ComponentConfigurationError(
            "REQUEST_LOGGING.EXCLUDED_FIELDS_BY_PATH must be a mapping"
        )
    request["EXCLUDED_FIELDS_BY_PATH"] = {
        path: _string_sequence(
            fields, f"REQUEST_LOGGING.EXCLUDED_FIELDS_BY_PATH.{path}"
        )
        for path, fields in by_path.items()
        if isinstance(path, str) and path.startswith("/")
    }
    if len(request["EXCLUDED_FIELDS_BY_PATH"]) != len(by_path):
        raise ComponentConfigurationError(
            "REQUEST_LOGGING.EXCLUDED_FIELDS_BY_PATH keys must be paths"
        )
    return {
        "ENABLED": enabled,
        "LOGGING": deepcopy(dict(logging_conf)),
        "COMPONENTS": deepcopy(dict(components)),
        "REQUEST_LOGGING": request,
    }
