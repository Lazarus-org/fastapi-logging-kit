"""Regression tests for the approved FASTAPI_LOGGING configuration contract."""

import logging
import logging.config
from copy import deepcopy

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from fastapi_logging_kit.app import setup_logging
from fastapi_logging_kit.settings.contract import compile_settings
from fastapi_logging_kit.settings.components import ComponentConfigurationError


def test_defaults_and_config_input_are_isolated():
    source = {"COMPONENTS": {}, "REQUEST_LOGGING": {"EXCLUDED_PATHS": ["/health"]}}
    saved = deepcopy(source)
    compiled = compile_settings(source)
    compiled["REQUEST_LOGGING"]["EXCLUDED_PATHS"].append("/metrics")
    assert source == saved
    assert compile_settings({})["REQUEST_LOGGING"]["QUERY_PARAMS_ENABLED"] is False


@pytest.mark.parametrize("conf, expected", [
    ({"TYPO": 1}, "Unknown FASTAPI_LOGGING"),
    ({"ENABLED": 1}, "ENABLED must be boolean"),
    ({"LOGGING": {"version": 2}}, "LOGGING.version"),
    ({"COMPONENTS": {"handlers": []}}, "COMPONENTS.handlers"),
    ({"REQUEST_LOGGING": {"ENABLED": 0}}, "REQUEST_LOGGING.ENABLED"),
    ({"REQUEST_LOGGING": {"MAX_BODY_BYTES": -1}}, "MAX_BODY_BYTES"),
    ({"REQUEST_LOGGING": {"TRUSTED_PROXIES": ["invalid"]}}, "Invalid trusted proxy"),
    ({"REQUEST_LOGGING": {"REQUEST_ID_HEADER": "X-ID\\r\\n"}}, "REQUEST_ID_HEADER"),
    ({"REQUEST_LOGGING": {"MAX_BODY_BYTES": 65_537}}, "between 0 and 65536"),
    ({"REQUEST_LOGGING": {"MAX_SQL_BYTES": 1_048_577}}, "between 0 and 1048576"),
    ({"REQUEST_LOGGING": {"MAX_DIAGNOSTIC_DEPTH": 17}}, "between 1 and 16"),
    ({"REQUEST_LOGGING": {"MAX_REQUEST_ID_LENGTH": 0}}, "MAX_REQUEST_ID_LENGTH"),
    ({"REQUEST_LOGGING": {"MAX_REQUEST_ID_LENGTH": 257}}, "MAX_REQUEST_ID_LENGTH"),
    ({"REQUEST_LOGGING": {"MAX_SQL_QUERIES": 0}}, "MAX_SQL_QUERIES"),
])
def test_malformed_config_fails_before_activation(conf, expected):
    with pytest.raises(ComponentConfigurationError, match=expected):
        compile_settings(conf)


def test_structured_default_preserves_host_handlers():
    root = logging.getLogger()
    host = logging.NullHandler()
    root.addHandler(host)
    original_level = root.level
    try:
        setup_logging(config={"COMPONENTS": {}})
        assert host in root.handlers
        assert root.level == original_level
    finally:
        root.removeHandler(host)


def test_configured_middleware_idempotent_and_disabled_routes(caplog):
    app = FastAPI()
    @app.get("/items")
    def items():
        return {"ok": True}
    @app.get("/health")
    def health():
        return {"ok": True}
    @app.get("/internal/status")
    def internal_status():
        return {"ok": True}
    config = {"REQUEST_LOGGING": {"EXCLUDED_PATHS": ["/health"], "EXCLUDED_PATH_PREFIXES": ["/internal"]}}
    setup_logging(app, config=config)
    setup_logging(app, config=config)
    assert len([m for m in app.user_middleware if m.cls.__name__ == "RequestLogMiddleware"]) == 1
    with pytest.raises(RuntimeError, match="different settings"):
        setup_logging(app, config={"REQUEST_LOGGING": {"EXCLUDED_PATHS": ["/different"]}})
    with TestClient(app) as client, caplog.at_level(logging.INFO, logger="fastapi_logging_kit.middleware.request_middleware"):
        response = client.get("/items", headers={"X-Request-ID": "my-request"})
        assert response.status_code == 200
        assert response.headers["x-request-id"] == "my-request"
        assert "REQUEST FINISHED" in caplog.text
        assert "REQUEST STARTED" not in caplog.text
        caplog.clear()
        assert client.get("/health").status_code == 200
        assert "REQUEST FINISHED" not in caplog.text
        caplog.clear()
        assert client.get("/internal/status").status_code == 200
        assert "REQUEST FINISHED" not in caplog.text


def test_opt_in_query_redaction(caplog):
    app = FastAPI()
    @app.get("/search")
    def search():
        return {"ok": True}
    setup_logging(app, config={"REQUEST_LOGGING": {"QUERY_PARAMS_ENABLED": True}})
    with TestClient(app) as client, caplog.at_level(logging.INFO, logger="fastapi_logging_kit.middleware.request_middleware"):
        assert client.get("/search?page=1&token=topsecret").status_code == 200
    assert '"page": "1"' in caplog.text
    assert "topsecret" not in caplog.text
    assert "[REDACTED]" in caplog.text


def test_explicit_logging_dictionary_is_not_mutated(monkeypatch):
    seen = []
    monkeypatch.setattr(logging.config, "dictConfig", lambda arg: seen.append(arg))
    config = {"LOGGING": {"version": 1, "handlers": {"sink": {"class": "logging.NullHandler"}}, "root": {"handlers": ["sink"]}}}
    original = deepcopy(config)
    setup_logging(config=config)
    assert config == original
    assert seen[0]["disable_existing_loggers"] is False

@pytest.mark.parametrize("conf, expected", [
    ([], "FASTAPI_LOGGING must be a mapping"),
    ({1: True}, "keys must be strings"),
    ({"LOGGING": []}, "LOGGING must be a dictConfig"),
    ({"LOGGING": {"version": 1, "incremental": True}}, "Incremental dictConfig"),
    ({"REQUEST_LOGGING": []}, "REQUEST_LOGGING must be a mapping"),
    ({"REQUEST_LOGGING": {"BOGUS": 1}}, "Unknown REQUEST_LOGGING"),
    ({"REQUEST_LOGGING": {"EXCLUDED_PATHS": ["relative"]}}, "requires absolute paths"),
    ({"REQUEST_LOGGING": {"EXCLUDED_FIELDS": "string"}}, "list of nonempty"),
    ({"REQUEST_LOGGING": {"EXCLUDED_FIELDS_BY_PATH": []}}, "must be a mapping"),
    ({"REQUEST_LOGGING": {"EXCLUDED_FIELDS_BY_PATH": {"relative": ["token"]}}}, "keys must be paths"),
])
def test_configuration_validation_negative_paths(conf, expected):
    with pytest.raises(ComponentConfigurationError, match=expected):
        compile_settings(conf)


def test_disabled_and_started_application_behaviors():
    app = FastAPI()
    setup_logging(app, config={"ENABLED": False})
    assert not app.user_middleware
    app.middleware_stack = object()
    with pytest.raises(RuntimeError, match="before starting"):
        setup_logging(app, config={"COMPONENTS": {}})


def test_custom_dictconfig_and_components_compiler(monkeypatch):
    captured = []
    monkeypatch.setattr(logging.config, "dictConfig", lambda conf: captured.append(conf))
    config = {
        "LOGGING": {"version": 1, "handlers": {}, "root": {"handlers": []}},
        "COMPONENTS": {
            "handlers": {"sink": {"class": "logging.NullHandler"}},
            "root_handlers": ["sink"],
        },
    }
    setup_logging(config=config)
    assert len(captured) == 1
    assert captured[0]["root"]["handlers"] == ["sink"]
    assert not any(key.startswith("_fast_") for key in captured[0])


def _request_scope(*, query=b"", client=("192.0.2.7", 2000), headers=None):
    return {
        "type": "http", "method": "GET", "path": "/search",
        "query_string": query, "client": client, "headers": headers or [],
        "server": ("localhost", 80), "scheme": "http", "http_version": "1.1",
    }


def _structured_middleware(**options):
    from fastapi_logging_kit.middleware import RequestLogMiddleware
    options = compile_settings({"REQUEST_LOGGING": options})["REQUEST_LOGGING"]
    async def downstream(scope, receive, send):
        return None
    return RequestLogMiddleware(downstream, config=options)


def test_query_diagnostics_bounds_repeated_keys_and_invalid_field_count():
    from starlette.requests import Request
    middleware = _structured_middleware(QUERY_PARAMS_ENABLED=True, MAX_QUERY_BYTES=15)
    assert middleware._query_diagnostic(Request(_request_scope())) is None
    assert middleware._query_diagnostic(Request(_request_scope(query=b"toolong=" + b"x" * 20))) == "<oversized query string>"
    middleware = _structured_middleware(QUERY_PARAMS_ENABLED=True, MAX_QUERY_BYTES=2000)
    assert middleware._query_diagnostic(Request(_request_scope(query=b"a=1&a=2"))) == '{"a": ["1", "2"]}'
    assert middleware._query_diagnostic(Request(_request_scope(query=b"&".join([b"a=1"] * 129)))) == "<unparseable query string>"
    assert middleware._query_diagnostic(Request(_request_scope(query=b"pin=123", headers=[]))) == '{"pin": "[REDACTED]"}'
    by_path = _structured_middleware(QUERY_PARAMS_ENABLED=True, EXCLUDED_FIELDS_BY_PATH={"/search": ["pin"]})
    assert "123" not in by_path._query_diagnostic(Request(_request_scope(query=b"pin=123")))


def test_client_ip_forwarding_requires_trusted_immediate_proxy():
    from starlette.requests import Request
    forged = [(b"x-forwarded-for", b"203.0.113.50, 198.51.100.9")]
    untrusted = _structured_middleware()
    scope = _request_scope(client=("192.0.2.7", 9000), headers=forged)
    assert untrusted._client_ip(Request(scope)) == "192.0.2.7"
    trusted = _structured_middleware(TRUSTED_PROXIES=["192.0.2.0/24"])
    assert trusted._client_ip(Request(scope)) == "198.51.100.9"
    all_trusted = _structured_middleware(TRUSTED_PROXIES=["0.0.0.0/0"])
    assert all_trusted._client_ip(Request(scope)) == "203.0.113.50"
    assert trusted._client_ip(Request(_request_scope(client=None))) == "Unknown IP"
    assert trusted._client_ip(Request(_request_scope(client=("not-an-ip", 1000)))) == "Unknown IP"
    assert trusted._client_ip(Request(_request_scope(client=("192.0.2.7", 9)))) == "192.0.2.7"
    malformed = [(b"x-forwarded-for", b"invalid, 198.51.100.9")]
    assert trusted._client_ip(Request(_request_scope(headers=malformed))) == "192.0.2.7"


def test_formatter_constructor_resolver_for_component_graph(tmp_path):
    from fastapi_logging_kit.settings.activation import activate
    from fastapi_logging_kit.settings.components import compile_components
    preset = {
        "version": 1,
        "handlers": {"custom": {"class": "logging.NullHandler", "formatter": "fmt"}},
        "formatters": {"fmt": {"class": "logging.Formatter", "format": "%(message)s"}},
        "filters": {}, "loggers": {}, "root": {"handlers": []},
    }
    graph = compile_components(preset, {"package_handlers": ["custom"]})
    paths = []
    resolver = logging.config.DictConfigurator({"version": 1}).resolve
    from fastapi_logging_kit.settings.activation import temporary_activation
    with temporary_activation(graph, resolver=lambda path: (paths.append(path), resolver(path))[1]):
        assert "logging.Formatter" in paths


def test_existing_isolated_compatibility(base_manager=None):
    from fastapi_logging_kit.settings.conf import LogManager
    assert callable(LogManager._set_isolated_conf)


def test_three_repeated_query_keys_and_context_key_rejection():
    from starlette.requests import Request
    from fastapi_logging_kit.contextvar.contextvar_manager import ContextVarManager
    middleware = _structured_middleware(QUERY_PARAMS_ENABLED=True)
    assert middleware._query_diagnostic(Request(_request_scope(query=b"k=1&k=2&k=3"))) == '{"k": ["1", "2", "3"]}'
    with pytest.raises(ValueError, match="non-empty unprefixed"):
        ContextVarManager().bind(fastapi_logging_kit_secret="x")


def test_external_rotation_handler_spec_and_legacy_isolated_helper(monkeypatch):
    from fastapi_logging_kit.settings.conf import LogConfig, LogManager
    conf = object.__new__(LogConfig)
    conf.log_rotation = {"TYPE": "external"}
    conf.log_rotation_overrides = {}
    instance = LogManager(conf)
    spec = instance._build_file_handler_config("/tmp/logging-example", "INFO")
    assert spec["class"] == "logging.handlers.WatchedFileHandler"
    calls = []
    monkeypatch.setattr(LogManager, "_set_owned_conf", classmethod(
        lambda cls, config, *, mode: calls.append(mode)
    ))
    LogManager._set_isolated_conf({})
    assert calls == ["isolated"]


def test_setup_without_explicit_settings_uses_additive_defaults(monkeypatch):
    from fastapi_logging_kit.settings import settings_manager
    monkeypatch.setattr(settings_manager, "log_settings", {})
    app = FastAPI()
    setup_logging(app)
    assert len([m for m in app.user_middleware if m.cls.__name__ == "RequestLogMiddleware"]) == 1
    assert app.state._fastapi_logging_kit_structured["REQUEST_LOGGING"]["QUERY_PARAMS_ENABLED"] is False


def test_explicit_loggers_with_components_do_not_replace_unspecified_root(monkeypatch):
    seen = []
    monkeypatch.setattr(logging.config, "dictConfig", lambda conf: seen.append(conf))
    setup_logging(config={
        "LOGGING": {"version": 1, "handlers": {"sink": {"class": "logging.NullHandler"}},
                    "loggers": {"integration.audit": {"handlers": ["sink"], "level": "INFO"}}},
        "COMPONENTS": {"handlers": {"extra": {"class": "logging.NullHandler"}}},
    })
    assert "root" not in seen[0]


def test_opt_in_request_body_is_bounded_and_redacted(caplog):
    app = FastAPI()

    @app.post("/submit")
    async def submit(payload: dict):
        return {"accepted": True, "received": payload["username"]}

    setup_logging(app, config={"REQUEST_LOGGING": {"REQUEST_BODY_ENABLED": True}})
    with TestClient(app) as client, caplog.at_level(
        logging.INFO, logger="fastapi_logging_kit.middleware.request_middleware"
    ):
        response = client.post(
            "/submit",
            json={"username": "alice", "password": "body-secret", "nested": {"api_key": "key-secret"}},
        )
    assert response.status_code == 200
    assert response.json() == {"accepted": True, "received": "alice"}
    assert '"username":"alice"' in caplog.text
    assert "body-secret" not in caplog.text
    assert "key-secret" not in caplog.text
    assert caplog.text.count("[REDACTED]") >= 2


def test_opt_in_error_response_body_is_bounded_and_redacted(caplog):
    from fastapi.responses import JSONResponse

    app = FastAPI()

    @app.get("/failure")
    async def failure():
        return JSONResponse(
            status_code=422,
            content={"detail": "invalid", "access_token": "response-secret"},
        )

    setup_logging(app, config={"REQUEST_LOGGING": {"ERROR_RESPONSE_BODY_ENABLED": True}})
    with TestClient(app) as client, caplog.at_level(
        logging.INFO, logger="fastapi_logging_kit.middleware.request_middleware"
    ):
        response = client.get("/failure")
    assert response.status_code == 422
    assert response.json()["access_token"] == "response-secret"
    assert '"detail":"invalid"' in caplog.text
    assert "response-secret" not in caplog.text
    assert "[REDACTED]" in caplog.text


def test_body_diagnostics_oversize_marker_does_not_log_payload(caplog):
    from fastapi.responses import JSONResponse

    app = FastAPI()

    @app.post("/submit")
    async def submit(payload: dict):
        return JSONResponse(status_code=400, content={"message": "x" * 100})

    setup_logging(
        app,
        config={
            "REQUEST_LOGGING": {
                "REQUEST_BODY_ENABLED": True,
                "ERROR_RESPONSE_BODY_ENABLED": True,
                "MAX_BODY_BYTES": 8,
                "MAX_ERROR_RESPONSE_BYTES": 8,
            }
        },
    )
    with TestClient(app) as client, caplog.at_level(
        logging.INFO, logger="fastapi_logging_kit.middleware.request_middleware"
    ):
        response = client.post("/submit", json={"password": "oversize-secret"})
    assert response.status_code == 400
    assert "<oversized request body>" in caplog.text
    assert "<oversized error response body>" in caplog.text
    assert "oversize-secret" not in caplog.text
    assert "x" * 50 not in caplog.text


def test_request_body_diagnostics_rejects_non_json_without_logging_raw_body(caplog):
    from fastapi import Request

    app = FastAPI()

    @app.post("/plain")
    async def plain(request: Request):
        return {"received": (await request.body()).decode()}

    setup_logging(app, config={"REQUEST_LOGGING": {"REQUEST_BODY_ENABLED": True}})
    with TestClient(app) as client, caplog.at_level(
        logging.INFO, logger="fastapi_logging_kit.middleware.request_middleware"
    ):
        response = client.post("/plain", content="do-not-log-this", headers={"content-type": "text/plain"})
    assert response.status_code == 200
    assert "<unsupported content type>" in caplog.text
    assert "do-not-log-this" not in caplog.text


def test_incomplete_request_body_is_marked_without_reading_request():
    from starlette.requests import Request
    from fastapi_logging_kit.middleware import RequestLogMiddleware

    compiled = compile_settings({"REQUEST_LOGGING": {"REQUEST_BODY_ENABLED": True}})
    async def downstream(scope, receive, send):
        return None
    middleware = RequestLogMiddleware(downstream, config=compiled["REQUEST_LOGGING"])
    request = Request({
        "type": "http", "method": "POST", "path": "/upload", "headers": [(b"content-type", b"application/json")],
        "query_string": b"", "client": ("127.0.0.1", 1234), "server": ("localhost", 80),
        "scheme": "http", "http_version": "1.1",
    })
    state = {
        "status_code": 200, "content_type": "application/json", "chunks": 1,
        "finalized": False, "cancelled": False, "request_body": bytearray(),
        "request_body_oversized": False, "request_body_complete": False,
        "error_body": bytearray(), "error_body_oversized": False,
    }
    assert "<incomplete request body>" in middleware._body_diagnostics(request, state)


def test_error_response_body_is_not_captured_for_success_status(caplog):
    app = FastAPI()

    @app.get("/success")
    async def success():
        return {"detail": "private-success-body"}

    setup_logging(app, config={"REQUEST_LOGGING": {"ERROR_RESPONSE_BODY_ENABLED": True}})
    with TestClient(app) as client, caplog.at_level(
        logging.INFO, logger="fastapi_logging_kit.middleware.request_middleware"
    ):
        response = client.get("/success")
    assert response.status_code == 200
    assert response.json()["detail"] == "private-success-body"
    assert "private-success-body" not in caplog.text
    assert "error_response_body=" not in caplog.text


def test_invalid_json_request_body_is_never_logged_raw(caplog):
    from fastapi import Request
    from fastapi.responses import JSONResponse

    app = FastAPI()

    @app.post("/invalid")
    async def invalid(request: Request):
        await request.body()
        return JSONResponse(status_code=400, content={"detail": "invalid"})

    setup_logging(app, config={"REQUEST_LOGGING": {"REQUEST_BODY_ENABLED": True}})
    raw = '{"password":"never-log-this"'
    with TestClient(app) as client, caplog.at_level(
        logging.INFO, logger="fastapi_logging_kit.middleware.request_middleware"
    ):
        response = client.post("/invalid", content=raw, headers={"content-type": "application/json"})
    assert response.status_code == 400
    assert "<invalid JSON body>" in caplog.text
    assert "never-log-this" not in caplog.text


def test_request_id_length_is_configurable():
    from starlette.requests import Request
    from uuid import UUID

    middleware = _structured_middleware(MAX_REQUEST_ID_LENGTH=8)
    request = Request(_request_scope(headers=[(b"x-request-id", b"too-long-id")]))
    generated = middleware._prepare_request(request)
    assert UUID(generated)
    accepted = Request(_request_scope(headers=[(b"x-request-id", b"short-id")]))
    assert middleware._prepare_request(accepted) == "short-id"



def test_query_diagnostic_output_size_is_bounded():
    from starlette.requests import Request

    middleware = _structured_middleware(
        QUERY_PARAMS_ENABLED=True,
        MAX_QUERY_BYTES=200,
    )
    query = "value=" + "é" * 80
    request = Request(_request_scope(query=query.encode("utf-8")))
    assert middleware._query_diagnostic(request) == "<oversized query string>"


def test_query_diagnostic_truncates_untrusted_field_names():
    from starlette.requests import Request

    middleware = _structured_middleware(
        QUERY_PARAMS_ENABLED=True,
        MAX_QUERY_BYTES=4096,
    )
    key = "x" * 300
    request = Request(_request_scope(query=f"{key}=secret".encode("ascii")))
    result = middleware._query_diagnostic(request)
    assert result is not None
    assert len(result) < 200
    assert "secret" not in result
    assert "[REDACTED]" in result




def test_sql_capture_propagates_into_sync_fastapi_endpoint(caplog):
    from fastapi_logging_kit.utils.sql import record_query

    app = FastAPI()

    @app.get("/db")
    def db_endpoint():
        record_query("SELECT sync_endpoint", 0.004)
        return {"ok": True}

    setup_logging(
        app,
        config={"REQUEST_LOGGING": {"LOG_SQL_QUERIES": True}},
    )
    with TestClient(app) as client, caplog.at_level(
        logging.INFO,
        logger="fastapi_logging_kit.middleware.request_middleware",
    ):
        response = client.get("/db")
    assert response.status_code == 200
    assert "SELECT sync_endpoint" in caplog.text
    assert "1 SQL QUERIES EXECUTED" in caplog.text
