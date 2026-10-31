"""Tests for the dictConfig component extension and activation contracts."""

import logging
import logging.handlers

import pytest

from fastapi_logging_kit.settings.activation import (
    activate,
    forget_controlled_loggers,
    temporary_activation,
)
from fastapi_logging_kit.settings.components import (
    ComponentConfigurationError,
    compile_components,
    validate_components,
)
from fastapi_logging_kit.settings.conf import LogConfig, LogManager


class AuditFormatter(logging.Formatter):
    """Prefix formatted records for component integration tests."""

    def format(self, record):
        return f"AUDIT:{record.getMessage()}"


class AuditFilter(logging.Filter):
    """Drop one known message to prove custom filters are active."""

    def filter(self, record):
        return record.getMessage() != "rejected"


class InvalidHandlerFactory:
    """Factory returning an invalid non-handler object."""

    def __new__(cls):
        return object()


@pytest.fixture
def base_manager(tmp_path):
    """Return a manager with small file presets for component tests."""
    config = LogConfig(
        log_levels=["INFO", "ERROR"],
        log_dir=str(tmp_path),
        log_file_formats={"INFO": "%(message)s", "ERROR": "%(message)s"},
        log_file_format_types={"INFO": "NORMAL", "ERROR": "NORMAL"},
        extra_log_files={"INFO": False, "ERROR": False},
        console_level="INFO",
        console_format="%(message)s",
        colorize_console=False,
        log_date_format="%Y-%m-%d",
        log_email_notifier_enable=False,
        log_email_notifier_log_levels=[],
        log_email_notifier_log_format=1,
    )
    manager = LogManager(config)
    manager.create_log_files()
    return manager


@pytest.fixture
def logger_state():
    """Restore all loggers and package activation ownership after each test."""
    root = logging.getLogger()
    package = logging.getLogger("fastapi_logging_kit")
    audit = logging.getLogger("component_test.audit")
    rollback = logging.getLogger("component_test.rollback")
    owners = (root, package, audit, rollback)
    original = {
        owner: (list(owner.handlers), list(owner.filters), owner.level, owner.propagate)
        for owner in owners
    }
    try:
        yield
    finally:
        for owner, (handlers, filters, level, propagate) in original.items():
            for handler in list(owner.handlers):
                if handler not in handlers:
                    owner.removeHandler(handler)
            for handler in handlers:
                if handler not in owner.handlers:
                    owner.addHandler(handler)
            for log_filter in list(owner.filters):
                if log_filter not in filters:
                    owner.removeFilter(log_filter)
            for log_filter in filters:
                if log_filter not in owner.filters:
                    owner.addFilter(log_filter)
            owner.setLevel(level)
            owner.propagate = propagate
        forget_controlled_loggers()


def test_validate_components_rejects_non_mapping_and_unknown_keys():
    with pytest.raises(ComponentConfigurationError, match="must be a dictionary"):
        validate_components([])
    with pytest.raises(ComponentConfigurationError, match="keys must be strings"):
        validate_components({1: {}})
    with pytest.raises(ComponentConfigurationError, match="Unknown COMPONENTS"):
        validate_components({"unknown": {}})


@pytest.mark.parametrize(
    "extension, message",
    [
        ({"handlers": []}, "COMPONENTS.handlers must be a dictionary"),
        ({"replace": {"unknown": {}}}, "unknown sections"),
        ({"disable": {"handlers": "file"}}, "must be a list of names"),
        ({"root_handlers": "console"}, "must be a list of names"),
        ({"package_handlers": ["x", "x"]}, "duplicate names"),
        ({"formatters": {"": {}}}, "map nonempty names"),
        ({"formatters": {"x": []}}, "map nonempty names"),
    ],
)
def test_validate_components_rejects_invalid_shapes(extension, message):
    with pytest.raises(ComponentConfigurationError, match=message):
        validate_components(extension)


def test_compile_components_add_replace_disable_and_copy(base_manager):
    preset = base_manager.build_logging_dict()
    original = preset.copy()
    compiled = compile_components(
        preset,
        {
            "formatters": {"audit": {"()": AuditFormatter}},
            "handlers": {
                "audit": {
                    "class": "logging.NullHandler",
                    "formatter": "audit",
                }
            },
            "replace": {
                "formatters": {"console": {"format": "%(message)s"}},
            },
            "disable": {"handlers": ["error"]},
            "package_handlers": ["audit"],
        },
    )
    assert "audit" in compiled["handlers"]
    assert "error" not in compiled["handlers"]
    assert "error" not in compiled["root"]["handlers"]
    assert compiled["_fast_explicit_package_handlers"] == ["audit"]
    assert "error" in original["handlers"]


def test_compile_components_rejects_collision_and_unknown_replacement(base_manager):
    preset = base_manager.build_logging_dict()
    with pytest.raises(ComponentConfigurationError, match="already exists"):
        compile_components(preset, {"handlers": {"info": {"class": "logging.NullHandler"}}})
    with pytest.raises(ComponentConfigurationError, match="does not exist"):
        compile_components(preset, {"replace": {"handlers": {"missing": {"class": "logging.NullHandler"}}}})


def test_compile_components_rejects_unknown_disabled_component(base_manager):
    with pytest.raises(ComponentConfigurationError, match="does not exist"):
        compile_components(base_manager.build_logging_dict(), {"disable": {"filters": ["missing"]}})


@pytest.mark.parametrize(
    "extension, message",
    [
        ({"handlers": {"broken": {}}}, "requires exactly one"),
        ({"handlers": {"broken": {"class": "logging.NullHandler", "()": logging.NullHandler}}}, "exactly one"),
        ({"handlers": {"broken": {"class": "logging.NullHandler", "formatter": "missing"}}}, "missing formatter"),
        ({"handlers": {"broken": {"class": "logging.NullHandler", "filters": ["missing"]}}}, "missing filters"),
        ({"loggers": {"audit": {"unknown": True}}}, "unsupported options"),
        ({"loggers": {"audit": {"handlers": ["missing"]}}}, "missing handlers"),
        ({"loggers": {"audit": {"filters": ["missing"]}}}, "missing filters"),
        ({"loggers": {"audit": {"propagate": "yes"}}}, "must be boolean"),
        ({"root_handlers": ["missing"]}, "unknown handlers"),
        ({"package_handlers": ["missing"]}, "unknown handlers"),
        ({"loggers": {"fastapi_logging_kit": {}}}, "managed loggers"),
        ({"loggers": {"root": {}}}, "managed loggers"),
    ],
)
def test_compile_components_rejects_broken_references(base_manager, extension, message):
    with pytest.raises(ComponentConfigurationError, match=message):
        compile_components(base_manager.build_logging_dict(), extension)


def test_compile_components_validates_root_and_section_types():
    with pytest.raises(ComponentConfigurationError, match="LOGGING.handlers"):
        compile_components({"handlers": []}, {})
    with pytest.raises(ComponentConfigurationError, match="LOGGING.root"):
        compile_components({"root": []}, {})
    with pytest.raises(ComponentConfigurationError, match="root.handlers"):
        compile_components({"root": {"handlers": "console"}}, {})


def test_custom_handler_formatter_filter_and_logger_activate(base_manager, logger_state):
    output = base_manager.log_config.log_dir + "/audit.log"
    base_manager.log_config.components = {
        "formatters": {"audit": {"()": AuditFormatter}},
        "filters": {"audit": {"()": AuditFilter}},
        "handlers": {
            "audit": {
                "class": "logging.FileHandler",
                "filename": output,
                "formatter": "audit",
                "filters": ["audit"],
            }
        },
        "loggers": {
            "component_test.audit": {
                "handlers": ["audit"],
                "filters": ["audit"],
                "level": "INFO",
                "propagate": False,
            }
        },
    }
    base_manager.set_conf(mode="additive")
    logger = logging.getLogger("component_test.audit")
    logger.info("allowed")
    logger.info("rejected")
    assert open(output, encoding="utf-8").read().splitlines() == ["AUDIT:allowed"]
    base_manager.set_conf(mode="additive")
    logger.info("only once")
    assert open(output, encoding="utf-8").read().count("only once") == 1
    assert sum(isinstance(item, AuditFilter) for item in logger.filters) == 1


def test_additive_activation_preserves_host_root_handlers(base_manager, logger_state):
    root = logging.getLogger()
    host_handler = logging.NullHandler()
    root.addHandler(host_handler)
    base_manager.set_conf(mode="additive")
    assert host_handler in root.handlers
    assert logging.getLogger("fastapi_logging_kit").propagate is True
    assert any(getattr(handler, "_fastapi_logging_kit_owned", False) for handler in root.handlers)


def test_explicit_root_handler_is_attached_once(base_manager, logger_state):
    root = logging.getLogger()
    base_manager.log_config.components = {
        "handlers": {"audit": {"class": "logging.NullHandler"}},
        "root_handlers": ["audit"],
    }
    base_manager.set_conf(mode="additive")
    base_manager.set_conf(mode="additive")
    assert len([h for h in root.handlers if h.name == "fastapi_logging_kit:audit"]) == 1


def test_disabled_handler_is_not_attached(base_manager, logger_state):
    base_manager.log_config.components = {"disable": {"handlers": ["error"]}}
    base_manager.set_conf(mode="isolated")
    package = logging.getLogger("fastapi_logging_kit")
    assert not any(handler.name == "fastapi_logging_kit:error" for handler in package.handlers)
    assert package.propagate is False


def test_factory_handler_dependency_is_constructed_in_order(base_manager, logger_state):
    base_manager.log_config.components = {
        "handlers": {
            "buffer": {
                "class": "logging.handlers.MemoryHandler",
                "capacity": 5,
                "target": "sink",
            },
            "sink": {"()": logging.NullHandler},
        },
        "package_handlers": ["buffer"],
    }
    base_manager.set_conf(mode="isolated")
    buffer = next(
        handler for handler in logging.getLogger("fastapi_logging_kit").handlers
        if handler.name == "fastapi_logging_kit:buffer"
    )
    assert isinstance(buffer, logging.handlers.MemoryHandler)
    assert isinstance(buffer.target, logging.NullHandler)


def test_unattached_custom_component_is_not_instantiated(base_manager, logger_state):
    class UnusedHandler(logging.Handler):
        def __init__(self):
            raise AssertionError("unused handler was instantiated")

        def emit(self, record):
            return None

    base_manager.log_config.components = {
        "handlers": {"unused": {"()": UnusedHandler}},
    }
    base_manager.set_conf(mode="isolated")
    assert not any(
        handler.name == "fastapi_logging_kit:unused"
        for handler in logging.getLogger("fastapi_logging_kit").handlers
    )


def test_invalid_factory_does_not_replace_active_handlers(base_manager, logger_state):
    base_manager.set_conf(mode="isolated")
    package = logging.getLogger("fastapi_logging_kit")
    previous = list(package.handlers)
    base_manager.log_config.components = {
        "handlers": {"broken": {"class": "not_a_real_module.Handler"}},
        "package_handlers": ["broken"],
    }
    with pytest.raises((ImportError, AttributeError, ValueError)):
        base_manager.set_conf(mode="isolated")
    assert package.handlers == previous


def test_invalid_handler_factory_result_is_rejected(base_manager, logger_state):
    base_manager.log_config.components = {
        "handlers": {"invalid": {"()": InvalidHandlerFactory}},
        "package_handlers": ["invalid"],
    }
    with pytest.raises(TypeError, match="did not produce"):
        base_manager.set_conf(mode="isolated")


def test_handler_dependency_cycle_is_rejected(base_manager, logger_state):
    base_manager.log_config.components = {
        "handlers": {
            "first": {"class": "logging.handlers.MemoryHandler", "capacity": 1, "target": "second"},
            "second": {"class": "logging.handlers.MemoryHandler", "capacity": 1, "target": "first"},
        },
        "package_handlers": ["first"],
    }
    with pytest.raises(ValueError, match="dependency cycle"):
        base_manager.set_conf(mode="isolated")


def test_temporary_activation_restores_logger_graph(base_manager, logger_state):
    package = logging.getLogger("fastapi_logging_kit")
    before_handlers = list(package.handlers)
    before_level = package.level
    base_manager.log_config.components = {
        "handlers": {"temporary": {"class": "logging.NullHandler"}},
        "package_handlers": ["temporary"],
    }
    config = base_manager.build_logging_dict()
    with temporary_activation(config, resolver=base_manager._resolve_class):
        assert any(handler.name == "fastapi_logging_kit:temporary" for handler in package.handlers)
    assert package.handlers == before_handlers
    assert package.level == before_level


def test_activate_rejects_invalid_mode(base_manager):
    config = base_manager.build_logging_dict()
    with pytest.raises(ValueError, match="Unsupported owned logging mode"):
        activate(config, mode="unknown", resolver=base_manager._resolve_class)


def test_explicit_dictconfig_is_applied_and_private_metadata_is_removed(base_manager, logger_state):
    base_manager.log_config.logging_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "handlers": {"null": {"class": "logging.NullHandler"}},
        "loggers": {"custom_dict_config": {"handlers": ["null"], "level": "INFO", "propagate": False}},
    }
    base_manager.set_conf(mode="additive")
    assert any(
        isinstance(handler, logging.NullHandler)
        for handler in logging.getLogger("custom_dict_config").handlers
    )


def test_custom_dictconfig_package_handlers_are_attached(base_manager, logger_state):
    base_manager.log_config.logging_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "handlers": {"custom": {"class": "logging.NullHandler"}},
    }
    base_manager.log_config.components = {"package_handlers": ["custom"]}
    base_manager.set_conf(mode="additive")
    assert any(
        isinstance(handler, logging.NullHandler)
        for handler in logging.getLogger("fastapi_logging_kit").handlers
    )


def test_incremental_dictconfig_rejects_components(base_manager):
    base_manager.log_config.logging_config = {"version": 1, "incremental": True}
    base_manager.log_config.components = {"package_handlers": ["missing"]}
    with pytest.raises(ComponentConfigurationError, match="incremental"):
        base_manager.build_logging_dict()


def test_validate_components_rejects_non_string_replace_section_name():
    with pytest.raises(ComponentConfigurationError, match="section names must be strings"):
        validate_components({"replace": {1: {}}})


def test_validate_components_rejects_non_mapping_replace_definitions():
    with pytest.raises(ComponentConfigurationError, match="must be a dictionary"):
        validate_components({"replace": {"handlers": []}})


def test_compile_components_rejects_malformed_existing_logger(base_manager):
    preset = base_manager.build_logging_dict()
    preset["loggers"]["malformed"] = None
    with pytest.raises(ComponentConfigurationError, match="loggers entries"):
        compile_components(preset, {})


def test_compile_components_rejects_malformed_existing_handler(base_manager):
    preset = base_manager.build_logging_dict()
    preset["handlers"]["malformed"] = None
    with pytest.raises(ComponentConfigurationError, match="Handler 'malformed'"):
        compile_components(preset, {})


def test_compile_components_rejects_missing_root_handler(base_manager):
    preset = base_manager.build_logging_dict()
    preset["root"]["handlers"].append("missing")
    with pytest.raises(ComponentConfigurationError, match="Root refers to missing handlers"):
        compile_components(preset, {})


class FanoutHandler(logging.Handler):
    """A handler whose configuration references other named handlers."""

    def __init__(self, handlers):
        super().__init__()
        self.handlers = handlers

    def emit(self, record):
        return None


def test_handler_handler_references_are_included_in_dependency_graph(base_manager, logger_state):
    base_manager.log_config.components = {
        "handlers": {
            "fanout": {
                "()": FanoutHandler,
                "handlers": ["sink"],
            },
            "sink": {"class": "logging.NullHandler"},
        },
        "package_handlers": ["fanout"],
    }
    base_manager.set_conf(mode="isolated")
    fanout = next(
        handler for handler in logging.getLogger("fastapi_logging_kit").handlers
        if handler.name == "fastapi_logging_kit:fanout"
    )
    assert isinstance(fanout, FanoutHandler)
    assert fanout.handlers == ["sink"]


def test_activation_rolls_back_logger_graph_when_attachment_fails(base_manager, logger_state, monkeypatch):
    target_logger = logging.getLogger("component_test.rollback")
    original_root = list(logging.getLogger().handlers)
    original_package = list(logging.getLogger("fastapi_logging_kit").handlers)
    original_filter = logging.Filter()
    target_logger.addFilter(original_filter)

    def fail_add_handler(handler):
        raise RuntimeError("attachment failed")

    monkeypatch.setattr(target_logger, "addHandler", fail_add_handler)
    base_manager.log_config.components = {
        "handlers": {"custom": {"class": "logging.NullHandler"}},
        "loggers": {
            "component_test.rollback": {
                "handlers": ["custom"],
                "level": "INFO",
                "propagate": False,
            }
        },
    }
    with pytest.raises(RuntimeError, match="attachment failed"):
        base_manager.set_conf(mode="additive")
    assert logging.getLogger().handlers == original_root
    assert logging.getLogger("fastapi_logging_kit").handlers == original_package
    assert target_logger.handlers == []
    assert target_logger.filters == [original_filter]


def test_custom_dictconfig_without_root_does_not_add_root_configuration(base_manager, logger_state):
    root = logging.getLogger()
    before_level = root.level
    base_manager.log_config.logging_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "handlers": {"null": {"class": "logging.NullHandler"}},
        "loggers": {"custom_no_root": {"handlers": ["null"], "level": "INFO"}},
    }
    config = base_manager.build_logging_dict()
    assert "root" not in config
    base_manager.set_conf()
    assert root.level == before_level


def test_custom_dictconfig_incremental_without_components_is_preserved(base_manager):
    base_manager.log_config.logging_config = {
        "version": 1,
        "incremental": True,
        "loggers": {"existing": {"level": "WARNING"}},
    }
    assert base_manager.build_logging_dict() == base_manager.log_config.logging_config


def test_component_resolver_rejects_invalid_and_missing_paths(base_manager):
    with pytest.raises(ValueError, match="Invalid import path"):
        base_manager._resolve_class("NotAQualifiedPath")
    with pytest.raises(ImportError, match="Cannot resolve component"):
        base_manager._resolve_class("fastapi_logging_kit.settings.conf.DoesNotExist")


def test_set_conf_rejects_unknown_mode(base_manager):
    with pytest.raises(ValueError, match="mode must be"):
        base_manager.set_conf(mode="unknown")


def test_replace_root_mode_attaches_explicit_package_handlers(base_manager, logger_state):
    base_manager.log_config.components = {
        "handlers": {"package_audit": {"class": "logging.NullHandler"}},
        "package_handlers": ["package_audit"],
    }
    base_manager.set_conf(mode="replace_root")
    package = logging.getLogger("fastapi_logging_kit")
    assert any(isinstance(handler, logging.NullHandler) for handler in package.handlers)
    assert package.propagate is False


def test_disabling_filter_removes_its_references(base_manager):
    compiled = compile_components(
        base_manager.build_logging_dict(),
        {"disable": {"filters": ["context_var_filter"]}},
    )
    assert "context_var_filter" not in compiled["filters"]
    assert all(
        "context_var_filter" not in handler.get("filters", [])
        for handler in compiled["handlers"].values()
    )


def test_disabling_formatter_removes_its_handler_references(base_manager):
    compiled = compile_components(
        base_manager.build_logging_dict(),
        {"disable": {"formatters": ["info"]}},
    )
    assert "info" not in compiled["formatters"]
    assert "formatter" not in compiled["handlers"]["info"]


def test_compile_components_rejects_non_mapping_base_formatter(base_manager):
    preset = base_manager.build_logging_dict()
    preset["formatters"]["broken"] = None
    with pytest.raises(ComponentConfigurationError, match="LOGGING.formatters.broken"):
        compile_components(preset, {})


def test_compile_components_rejects_non_mapping_base_filter(base_manager):
    preset = base_manager.build_logging_dict()
    preset["filters"]["broken"] = None
    with pytest.raises(ComponentConfigurationError, match="LOGGING.filters.broken"):
        compile_components(preset, {})
