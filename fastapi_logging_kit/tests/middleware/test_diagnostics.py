"""Tests for bounded JSON request/response diagnostic serialization."""

import pytest

from fastapi_logging_kit.middleware.diagnostics import format_json_diagnostic


def test_empty_body_is_not_logged():
    assert format_json_diagnostic(
        b"", "application/json", excluded_fields=[], max_depth=8
    ) is None


def test_unsupported_media_type_is_not_decoded():
    assert format_json_diagnostic(
        b"password=secret",
        "text/plain",
        excluded_fields=[],
        max_depth=8,
    ) == "<unsupported content type>"


def test_json_suffix_media_type_is_supported_and_redacted():
    result = format_json_diagnostic(
        b'{"profile":{"email":"private@example.com","name":"Ada"}}',
        "application/problem+json; charset=utf-8",
        excluded_fields=[],
        max_depth=8,
    )
    assert result == '{"profile":{"email":"[REDACTED]","name":"Ada"}}'


@pytest.mark.parametrize("body", [b"not-json", b"{\"bad\": NaN}", b"\xff"])
def test_invalid_json_returns_marker(body):
    assert format_json_diagnostic(
        body, "application/json", excluded_fields=[], max_depth=8
    ) == "<invalid JSON body>"


def test_custom_excluded_fields_and_depth_limit():
    result = format_json_diagnostic(
        b'{"outer":{"custom_value":"secret","deeper":{"value":1}}}',
        "application/json",
        excluded_fields=["custom-value"],
        max_depth=1,
    )
    assert result == '{"outer":{"custom_value":"[REDACTED]","deeper":"[OMITTED]"}}'


def test_large_arrays_are_bounded_by_node_budget():
    body = ("[" + ",".join("0" for _ in range(2100)) + "]").encode()
    result = format_json_diagnostic(
        body, "application/json", excluded_fields=[], max_depth=8
    )
    assert result.endswith('"[OMITTED]"]')


def test_very_long_keys_are_redacted_and_truncated():
    key = "x" * 300
    result = format_json_diagnostic(
        ("{" + __import__("json").dumps(key) + ":\"sensitive\"}").encode(),
        "application/json",
        excluded_fields=[],
        max_depth=8,
    )
    assert "sensitive" not in result
    assert "[REDACTED]" in result
    assert len(result) < 200


def test_node_budget_exhaustion_for_scalar_and_mapping(monkeypatch):
    import fastapi_logging_kit.middleware.diagnostics as diagnostics

    monkeypatch.setattr(diagnostics, "_MAX_NODES", 0)
    assert format_json_diagnostic(
        b'[]', "application/json", excluded_fields=[], max_depth=8
    ) == '"[OMITTED]"'
    monkeypatch.setattr(diagnostics, "_MAX_NODES", 1)
    assert format_json_diagnostic(
        b'{"field":1}', "application/json", excluded_fields=[], max_depth=8
    ) == '{"[remaining fields]":"[OMITTED]"}'


def test_list_depth_limit_and_unexpected_python_value():
    import fastapi_logging_kit.middleware.diagnostics as diagnostics

    assert format_json_diagnostic(
        b'[[[]]]', "application/json", excluded_fields=[], max_depth=0
    ) == '["[OMITTED]"]'
    assert diagnostics._sanitize_json_value(
        object(), excluded_fields=frozenset(), depth=0, max_depth=8, budget=[10]
    ) == "[OMITTED]"


def test_content_type_without_json_subtype_is_not_json():
    from fastapi_logging_kit.middleware.diagnostics import is_json_content_type

    assert is_json_content_type("application/vnd.example+json; charset=utf-8")
    assert not is_json_content_type("text/plain")
    assert not is_json_content_type("invalid-media-type")
    assert not is_json_content_type("text/example+json")


def test_sensitive_field_name_uses_default_and_custom_rules():
    from fastapi_logging_kit.middleware.diagnostics import is_sensitive_field

    assert is_sensitive_field("user_email", [])
    assert is_sensitive_field("custom-field", ["custom_field"])
    assert not is_sensitive_field("display_name", [])


def test_direct_middleware_configuration_is_normalized_with_defaults():
    from fastapi_logging_kit.middleware import RequestLogMiddleware

    async def downstream(scope, receive, send):
        return None

    middleware = RequestLogMiddleware(
        downstream,
        config={"EXCLUDED_PATH_PREFIXES": ["/internal/"]},
    )
    assert middleware.configuration["REQUEST_BODY_ENABLED"] is False
    assert middleware.excluded_prefixes == ("/internal",)



def test_output_byte_limit_and_unstructured_json_markers():
    assert format_json_diagnostic(
        b'{"value":"long text"}', "application/json", excluded_fields=[],
        max_depth=8, max_output_bytes=4,
    ) == "<oversized diagnostic>"
    assert format_json_diagnostic(
        b'"plain scalar"', "application/json", excluded_fields=[], max_depth=8
    ) == "<unstructured JSON body>"


def test_safe_path_and_user_agent_sanitization():
    from fastapi_logging_kit.middleware.diagnostics import safe_path, sanitize_user_agent

    assert safe_path("/a\r\nb") == "/a??b"
    assert safe_path("/" + "x" * 300) == "/" + "x" * 255
    assert sanitize_user_agent("Agent/1.0\r\nsecret") == "Agent/1.0"
    assert sanitize_user_agent("no-product-token") == "Unknown User Agent"

