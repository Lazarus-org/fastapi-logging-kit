"""Resource and process-isolation tests for background SMTP notifications."""
import os
import runpy
import threading
from unittest.mock import MagicMock, patch

import pytest

from fastapi_logging_kit.settings import settings_manager
from fastapi_logging_kit.utils.log_email_notifier import notifier
from fastapi_logging_kit.validators.config_validators import validate_email_notifier


def test_import_registers_child_fork_reset_when_supported(monkeypatch):
    register = MagicMock()
    monkeypatch.setattr(os, "register_at_fork", register, raising=False)

    module = runpy.run_path(notifier.__file__)

    register.assert_called_once_with(after_in_child=module["_after_fork"])
    semaphore = module["_semaphore"](1)
    lock = module["_after_fork"].__globals__["_limiter_lock"]
    register.call_args.kwargs["after_in_child"]()
    assert module["_after_fork"].__globals__["_limiter_lock"] is not lock
    assert module["_semaphore"](1) is not semaphore


def test_email_concurrency_is_bounded_and_rejected_event_is_not_blocked():
    started = threading.Event()
    release = threading.Event()
    finished = threading.Event()
    settings_manager.load({"LOG_EMAIL_NOTIFIER": {"MAX_CONCURRENT": 1, "SMTP_TIMEOUT": 2}})

    def block_delivery(*args, **kwargs):
        started.set()
        assert release.wait(5)
        raise OSError("simulated")

    try:
        with patch.object(notifier, "SMTP", side_effect=block_delivery):
            assert notifier.send_email_async("one", "body", ["admin@example.com"], finished)
            assert started.wait(5)
            dropped = threading.Event()
            assert notifier.send_email_async("two", "body", ["admin@example.com"], dropped) is False
            assert dropped.is_set()
    finally:
        release.set()
        assert finished.wait(5)
        settings_manager.reset()


def test_invalid_resource_limits_fail_before_email_delivery():
    for key, bad in (("MAX_CONCURRENT", 0), ("MAX_CONCURRENT", True), ("SMTP_TIMEOUT", 121), ("SMTP_TIMEOUT", "infinite")):
        settings_manager.load({"LOG_EMAIL_NOTIFIER": {key: bad}})
        assert validate_email_notifier(settings_manager.email_notifier)
        with patch.object(notifier, "SMTP") as smtp, pytest.raises(ValueError):
            notifier.send_email_async("subject", "body", ["a@example.com"])
            smtp.assert_not_called()
    settings_manager.reset()


def test_smtp_timeout_is_configurable(configure_email_settings, mock_smtp):
    settings_manager.load({"EMAIL": configure_email_settings, "LOG_EMAIL_NOTIFIER": {"SMTP_TIMEOUT": 3}})
    msg = MagicMock()
    notifier._deliver(msg, ["admin@example.com"])
    mock_smtp.assert_called_once_with("smtp.example.com", 587, timeout=3)


def test_prefork_limiter_state_is_reset_and_capacity_switches():
    settings_manager.load({"LOG_EMAIL_NOTIFIER": {"MAX_CONCURRENT": 1}})
    first = notifier._semaphore(1)
    assert notifier._semaphore(1) is first
    assert notifier._semaphore(2) is not first
    with patch.object(notifier.os, "getpid", return_value=os.getpid() + 1):
        assert notifier._semaphore(2) is not first
    notifier._after_fork()
    assert notifier._semaphore(1) is not first
    settings_manager.reset()


def test_worker_start_failure_releases_capacity_and_signals():
    settings_manager.load({"LOG_EMAIL_NOTIFIER": {"MAX_CONCURRENT": 1}})
    event = threading.Event()
    with patch.object(notifier.threading.Thread, "start", side_effect=RuntimeError("unavailable")), pytest.raises(RuntimeError):
        notifier.send_email_async("subject", "body", ["admin@example.com"], event)
    assert event.is_set()
    assert notifier._semaphore(1).acquire(blocking=False)
    notifier._semaphore(1).release()
    settings_manager.reset()


def test_worker_exception_during_message_construction_signals_completion():
    settings_manager.load({"LOG_EMAIL_NOTIFIER": {"MAX_CONCURRENT": 1}})
    event = threading.Event()
    with patch.object(notifier, "get_email_setting", side_effect=ValueError("missing")):
        assert notifier.send_email_async("subject", "body", ["admin@example.com"], event)
        assert event.wait(5)
    assert notifier._semaphore(1).acquire(blocking=False)
    notifier._semaphore(1).release()
    settings_manager.reset()


def test_missing_notifier_options_use_safe_defaults(monkeypatch):
    monkeypatch.setattr(settings_manager, "email_notifier", None)
    assert notifier._options() == (4, 10)
