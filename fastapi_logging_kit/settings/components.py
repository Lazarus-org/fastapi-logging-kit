"""Compile explicit extensions to FastAPI Logging Kit's dictConfig presets.

The extension API keeps additions, replacements and removals separate. A component name
is never silently overwritten: use ``replace`` when replacing an existing preset or
configured component, and ``disable`` to remove one.

The compiler validates component references before any handlers are created or attached
to the process-wide logging graph.
"""

from collections.abc import Mapping
from copy import deepcopy
from typing import Any

from fastapi_logging_kit.exceptions import ImproperlyConfigured

SECTIONS = ("formatters", "filters", "handlers", "loggers")


class ComponentConfigurationError(ImproperlyConfigured):
    """Raised when ``FASTAPI_LOGGING['COMPONENTS']`` is invalid."""


def _names(value: Any, location: str) -> list[str]:
    """Validate and return a list of unique component names."""
    if not isinstance(value, (list, tuple)) or any(
        not isinstance(name, str) or not name for name in value
    ):
        raise ComponentConfigurationError(f"{location} must be a list of names")
    if len(value) != len(set(value)):
        raise ComponentConfigurationError(f"{location} contains duplicate names")
    return list(value)


def validate_components(extensions: Any) -> None:
    """Validate the extension mapping without importing application code."""
    # pylint: disable=too-many-branches
    if not isinstance(extensions, Mapping):
        raise ComponentConfigurationError("COMPONENTS must be a dictionary")

    allowed = set(SECTIONS) | {
        "replace",
        "disable",
        "root_handlers",
        "package_handlers",
    }
    if any(not isinstance(key, str) for key in extensions):
        raise ComponentConfigurationError("COMPONENTS keys must be strings")
    unknown = set(extensions) - allowed
    if unknown:
        raise ComponentConfigurationError(f"Unknown COMPONENTS keys: {sorted(unknown)}")

    for category in (*SECTIONS, "replace", "disable"):
        value = extensions.get(category, {})
        if not isinstance(value, Mapping):
            raise ComponentConfigurationError(
                f"COMPONENTS.{category} must be a dictionary"
            )
        if category in ("replace", "disable"):
            if any(not isinstance(key, str) for key in value):
                raise ComponentConfigurationError(
                    f"COMPONENTS.{category} section names must be strings"
                )
            invalid_sections = set(value) - set(SECTIONS)
            if invalid_sections:
                raise ComponentConfigurationError(
                    f"COMPONENTS.{category} contains unknown sections: "
                    f"{sorted(invalid_sections)}"
                )
            for section, entries in value.items():
                if category == "disable":
                    _names(entries, f"COMPONENTS.disable.{section}")
                else:
                    _validate_definitions(entries, f"COMPONENTS.replace.{section}")
        else:
            _validate_definitions(value, f"COMPONENTS.{category}")

    for group in ("root_handlers", "package_handlers"):
        _names(extensions.get(group, []), f"COMPONENTS.{group}")


def _validate_definitions(definitions: Any, location: str) -> None:
    """Ensure component definitions map names to configuration mappings."""
    if not isinstance(definitions, Mapping):
        raise ComponentConfigurationError(f"{location} must be a dictionary")
    for name, spec in definitions.items():
        if not isinstance(name, str) or not name or not isinstance(spec, Mapping):
            raise ComponentConfigurationError(
                f"{location} must map nonempty names to dictionaries"
            )


def _ensure_sections(config: dict) -> None:
    """Normalize optional dictConfig sections for reference validation."""
    for section in SECTIONS:
        config.setdefault(section, {})
        if not isinstance(config[section], Mapping):
            raise ComponentConfigurationError(f"LOGGING.{section} must be a dictionary")
        config[section] = dict(config[section])
    for section in ("formatters", "filters"):
        for name, spec in list(config[section].items()):
            if not isinstance(spec, Mapping):
                raise ComponentConfigurationError(
                    f"LOGGING.{section}.{name} must be a dictionary"
                )
            config[section][name] = dict(spec)
    config.setdefault("root", {"handlers": []})
    if not isinstance(config["root"], Mapping):
        raise ComponentConfigurationError("LOGGING.root must be a dictionary")
    root = dict(config["root"])
    root.setdefault("handlers", [])
    config["root"] = root


def compile_components(presets: Mapping[str, Any], extensions: Any) -> dict:
    """Return an independent, validated dictConfig mapping with routing hints.

    The returned private ``_fast_*`` fields are consumed by the package's non-
    destructive activator and must be stripped before calling
    ``logging.config.dictConfig``.
    """
    # pylint: disable=too-many-branches,too-many-statements
    validate_components(extensions)
    extensions = deepcopy(dict(extensions))
    config = deepcopy(dict(presets))
    _ensure_sections(config)

    original_handlers = list(config["handlers"])
    original_root_handlers = _names(
        config["root"].get("handlers", []), "LOGGING.root.handlers"
    )

    for section in SECTIONS:
        target = config[section]
        for name, spec in extensions.get(section, {}).items():
            if name in target:
                raise ComponentConfigurationError(
                    f"COMPONENTS.{section}.{name} already exists; "
                    f"use replace.{section}"
                )
            target[name] = dict(spec)
        for name, spec in extensions.get("replace", {}).get(section, {}).items():
            if name not in target:
                raise ComponentConfigurationError(
                    f"COMPONENTS.replace.{section}.{name} does not exist"
                )
            target[name] = dict(spec)
        for name in extensions.get("disable", {}).get(section, []):
            if name not in target:
                raise ComponentConfigurationError(
                    f"COMPONENTS.disable.{section}.{name} does not exist"
                )
            del target[name]

    removed = {
        section: set(presets.get(section, {})) - set(config[section])
        for section in SECTIONS
    }
    removed_handlers = removed["handlers"]
    removed_filters = removed["filters"]
    removed_formatters = removed["formatters"]

    config["root"]["handlers"] = [
        name for name in original_root_handlers if name not in removed_handlers
    ]
    for logger_name, original_spec in list(config["loggers"].items()):
        if not isinstance(original_spec, Mapping):
            raise ComponentConfigurationError(
                "LOGGING.loggers entries must be dictionaries"
            )
        logger_spec = dict(original_spec)
        if "handlers" in logger_spec:
            logger_spec["handlers"] = [
                name for name in logger_spec["handlers"] if name not in removed_handlers
            ]
        if "filters" in logger_spec:
            logger_spec["filters"] = [
                name for name in logger_spec["filters"] if name not in removed_filters
            ]
        config["loggers"][logger_name] = logger_spec

    for handler_name, original_spec in list(config["handlers"].items()):
        if not isinstance(original_spec, Mapping):
            raise ComponentConfigurationError(
                f"Handler {handler_name!r} must be a dictionary"
            )
        handler_spec = dict(original_spec)
        if "filters" in handler_spec:
            handler_spec["filters"] = [
                name for name in handler_spec["filters"] if name not in removed_filters
            ]
        if handler_spec.get("formatter") in removed_formatters:
            handler_spec.pop("formatter")
        config["handlers"][handler_name] = handler_spec

    explicit_root = extensions.get("root_handlers", [])
    explicit_package = extensions.get("package_handlers", [])
    for key, values in (
        ("root_handlers", explicit_root),
        ("package_handlers", explicit_package),
    ):
        missing = set(values) - set(config["handlers"])
        if missing:
            raise ComponentConfigurationError(
                f"COMPONENTS.{key} refers to unknown handlers: {sorted(missing)}"
            )
    config["root"]["handlers"] = list(
        dict.fromkeys(config["root"]["handlers"] + explicit_root)
    )

    # Validate component-to-component references before importing user code.
    for name, handler in config["handlers"].items():
        if ("class" in handler) == ("()" in handler):
            raise ComponentConfigurationError(
                f"Handler {name!r} requires exactly one of 'class' or '()'"
            )
        formatter = handler.get("formatter")
        if formatter is not None and (
            not isinstance(formatter, str) or formatter not in config["formatters"]
        ):
            raise ComponentConfigurationError(
                f"Handler {name!r} refers to missing formatter {formatter!r}"
            )
        filters = _names(handler.get("filters", []), f"handler {name!r}.filters")
        missing_filters = set(filters) - set(config["filters"])
        if missing_filters:
            raise ComponentConfigurationError(
                f"Handler {name!r} refers to missing filters: {sorted(missing_filters)}"
            )

    for name, logger_spec in config["loggers"].items():
        if set(logger_spec) - {"handlers", "filters", "level", "propagate"}:
            raise ComponentConfigurationError(
                f"Logger {name!r} contains unsupported options"
            )
        handlers = _names(logger_spec.get("handlers", []), f"logger {name!r}.handlers")
        missing_handlers = set(handlers) - set(config["handlers"])
        if missing_handlers:
            raise ComponentConfigurationError(
                f"Logger {name!r} refers to missing handlers: "
                f"{sorted(missing_handlers)}"
            )
        filters = _names(logger_spec.get("filters", []), f"logger {name!r}.filters")
        missing_filters = set(filters) - set(config["filters"])
        if missing_filters:
            raise ComponentConfigurationError(
                f"Logger {name!r} refers to missing filters: {sorted(missing_filters)}"
            )
        if "propagate" in logger_spec and not isinstance(
            logger_spec["propagate"], bool
        ):
            raise ComponentConfigurationError(
                f"Logger {name!r}.propagate must be boolean"
            )

    root_handlers = _names(config["root"].get("handlers", []), "LOGGING.root.handlers")
    missing_root = set(root_handlers) - set(config["handlers"])
    if missing_root:
        raise ComponentConfigurationError(
            f"Root refers to missing handlers: {sorted(missing_root)}"
        )

    explicit_loggers = set(extensions.get("loggers", {})) | set(
        extensions.get("replace", {}).get("loggers", {})
    )
    if "fastapi_logging_kit" in explicit_loggers or "root" in explicit_loggers:
        raise ComponentConfigurationError(
            "Use package_handlers/root_handlers instead of overriding managed loggers"
        )

    config["_fast_explicit_root_handlers"] = list(explicit_root)
    config["_fast_explicit_package_handlers"] = list(explicit_package)
    config["_fast_explicit_loggers"] = sorted(
        explicit_loggers - set(extensions.get("disable", {}).get("loggers", []))
    )
    config["_fast_package_handlers"] = [
        name for name in original_handlers if name in config["handlers"]
    ] + [name for name in explicit_package if name not in original_handlers]
    return config
