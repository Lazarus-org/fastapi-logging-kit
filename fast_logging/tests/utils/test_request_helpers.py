import sys
from typing import Any, Callable

import pytest
from starlette.requests import Request

from fast_logging.tests.constants import PYTHON_VERSION, PYTHON_VERSION_REASON
from fast_logging.tests.fixtures import DummyUser
from fast_logging.utils.request import (
    UNKNOWN_IP,
    UNKNOWN_USER_AGENT,
    get_ip_address,
    get_request_id,
    get_user,
    get_user_agent,
)

pytestmark = [
    pytest.mark.utils,
    pytest.mark.skipif(sys.version_info < PYTHON_VERSION, reason=PYTHON_VERSION_REASON),
]


class _PkUser:
    """A user identified by ``pk`` rather than ``id``."""

    def __init__(self) -> None:
        """Initialize the user."""
        self.username = "pk-user"
        self.pk = 42


class _NoIdentifierUser:
    """A user exposing neither ``id`` nor ``pk``."""

    def __init__(self) -> None:
        """Initialize the user."""
        self.username = "id-less"


class _NamelessUser:
    """A user exposing no name-like attribute at all."""

    id = 7

    def __str__(self) -> str:
        """Return the fallback description used as the username."""
        return "nameless-user"


class TestGetIpAddress:
    """Test suite for the `get_ip_address` helper."""

    def test_returns_cached_ip_address(
        self, request_factory: Callable[..., Request]
    ) -> None:
        """Test that a pre-computed `ip_address` attribute wins."""
        request = request_factory()
        request.ip_address = "10.0.0.9"

        assert get_ip_address(request) == "10.0.0.9"

    def test_uses_first_forwarded_for_entry(
        self, request_factory: Callable[..., Request]
    ) -> None:
        """Test that the first `X-Forwarded-For` entry is used."""
        request = request_factory(
            headers={"X-Forwarded-For": "  203.0.113.1 , 70.41.3.18 , 150.172.238.178 "}
        )

        assert get_ip_address(request) == "203.0.113.1"

    def test_empty_forwarded_for_falls_back_to_client(
        self, request_factory: Callable[..., Request]
    ) -> None:
        """Test that a blank `X-Forwarded-For` falls back to the peer."""
        request = request_factory(headers={"X-Forwarded-For": ""})

        assert get_ip_address(request) == "127.0.0.1"

    def test_whitespace_only_forwarded_for_falls_back_to_client(
        self, request_factory: Callable[..., Request]
    ) -> None:
        """Test that a whitespace-only `X-Forwarded-For` is ignored."""
        request = request_factory(headers={"X-Forwarded-For": "  ,   , "})

        assert get_ip_address(request) == "127.0.0.1"

    def test_falls_back_to_client_host(
        self, request_factory: Callable[..., Request]
    ) -> None:
        """Test that the peer address is used when no header is present."""
        request = request_factory(client=("192.168.1.10", 8000))

        assert get_ip_address(request) == "192.168.1.10"

    def test_returns_unknown_when_client_is_missing(
        self, request_factory: Callable[..., Request]
    ) -> None:
        """Test that a scope without a client yields the unknown marker."""
        request = request_factory(client=None)

        assert get_ip_address(request) == UNKNOWN_IP

    def test_returns_unknown_when_client_host_is_empty(
        self, request_factory: Callable[..., Request]
    ) -> None:
        """Test that a blank peer host yields the unknown marker."""
        request = request_factory(client=("", 0))

        assert get_ip_address(request) == UNKNOWN_IP


class TestGetUserAgent:
    """Test suite for the `get_user_agent` helper."""

    def test_returns_user_agent_header(
        self, request_factory: Callable[..., Request]
    ) -> None:
        """Test that the `User-Agent` header is returned when present."""
        request = request_factory(headers={"User-Agent": "pytest-agent/1.0"})

        assert get_user_agent(request) == "pytest-agent/1.0"

    def test_returns_default_when_absent(
        self, request_factory: Callable[..., Request]
    ) -> None:
        """Test that a missing `User-Agent` yields the unknown marker."""
        request = request_factory()

        assert get_user_agent(request) == UNKNOWN_USER_AGENT


class TestGetRequestId:
    """Test suite for the `get_request_id` helper."""

    def test_returns_request_id_header(
        self, request_factory: Callable[..., Request]
    ) -> None:
        """Test that the `X-Request-ID` header is returned when present."""
        request = request_factory(headers={"X-Request-ID": "abc-123"})

        assert get_request_id(request) == "abc-123"

    def test_returns_none_when_absent(
        self, request_factory: Callable[..., Request]
    ) -> None:
        """Test that a missing `X-Request-ID` header yields None."""
        request = request_factory()

        assert get_request_id(request) is None


class TestGetUser:
    """Test suite for the `get_user` helper."""

    def test_returns_anonymous_without_user(
        self, request_factory: Callable[..., Request]
    ) -> None:
        """Test that a scope carrying no user is reported as anonymous."""
        request = request_factory()

        assert get_user(request) == "Anonymous"

    def test_returns_anonymous_without_scope(self) -> None:
        """Test that an object without a scope is reported as anonymous."""

        class _Scopeless:
            """A request-like object with no scope."""

        assert get_user(_Scopeless()) == "Anonymous"

    def test_returns_anonymous_for_unauthenticated_user(
        self, request_factory: Callable[..., Request]
    ) -> None:
        """Test that a user with a falsy `is_authenticated` is anonymous."""
        user = DummyUser(is_authenticated=False)
        request = request_factory(user=user)

        assert get_user(request) == "Anonymous"

    def test_describes_authenticated_user(
        self, request_factory: Callable[..., Request], dummy_user: Any
    ) -> None:
        """Test that an authenticated user is described with name and ID."""
        request = request_factory(user=dummy_user)

        assert get_user(request) == "[tester (ID:1)]"

    def test_describes_superuser(
        self, request_factory: Callable[..., Request], superuser: Any
    ) -> None:
        """Test that the superuser fixture is described correctly."""
        request = request_factory(user=superuser)

        assert get_user(request) == "[root (ID:99)]"

    def test_falls_back_to_pk_identifier(
        self, request_factory: Callable[..., Request]
    ) -> None:
        """Test that `pk` is used when the user exposes no `id`."""
        request = request_factory(user=_PkUser())

        assert get_user(request) == "[pk-user (ID:42)]"

    def test_omits_identifier_when_absent(
        self, request_factory: Callable[..., Request]
    ) -> None:
        """Test that a user with neither `id` nor `pk` shows only a name."""
        request = request_factory(user=_NoIdentifierUser())

        assert get_user(request) == "[id-less]"

    def test_falls_back_to_str_for_nameless_user(
        self, request_factory: Callable[..., Request]
    ) -> None:
        """Test that `str(user)` is used when no name attribute is set."""
        request = request_factory(user=_NamelessUser())

        assert get_user(request) == "[nameless-user (ID:7)]"
