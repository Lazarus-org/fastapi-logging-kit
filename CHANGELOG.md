# Changelog

All notable changes to FastAPI Logging Kit are documented here.

## Unreleased

### Fixed

- Install documentation dependencies into the Read the Docs build virtualenv explicitly.
- Limit the legacy FastAPI test lane to Python 3.11–3.13; use the modern lane on Python 3.14 and 3.15 to avoid deprecated framework APIs.
- Use Poetry dependency groups and a lockfile instead of duplicate requirements manifests.
- Validate installed package metadata against the authoritative project dependencies.
- Remove test-client deprecations through compatible legacy dependencies and an updated modern stack.
- Make deprecation warnings fail the test suite.

- Fix tox bootstrap requirement parsing so compatibility environments can start.
- Cover modern router-container validation independently of the installed FastAPI version.

## 1.0.0 - 2026-11-01

First release of FastAPI Logging Kit.

### Added

- Add explicit FastAPI/ASGI setup with structured logging configuration and extensible components.
- Add JSON, XML, FLAT, and colored console formatters with bounded serialization and named-field redaction.
- Add isolated request context, request IDs, and opt-in request, response, streaming, and SQL diagnostics.
- Add synchronous and asynchronous execution tracking with optional SQLAlchemy instrumentation.
- Add per-level file handlers, size/time rotation, gzip archives, SMTP notifications, and maintenance commands.
- Add the LogiBoard interface with application-scoped permission checks.
- Add contribution and publishing guides, including synchronized Commitizen version increments.
- Add Python 3.15 to the compatibility matrix and package classifiers.
- Add regression coverage for LogiBoard installation conflicts, repeated setup, and application-scoped permission policies.
- Add browser-side security regressions for archive filenames and ZIP folder-tree construction.
- Add permission-callback regression coverage for asynchronous and non-boolean fail-open cases.
- Add a PEP 561 typing marker and distribution-content verification.
- Add CI jobs for wheel/source-distribution builds, installed-package smoke tests, type checking, and linting.

### Changed

- Explicitly include LogiBoard static assets, HTML templates, and the PEP 561 marker in wheels and source distributions.
- Use the PyPI SQLAlchemy extra consistently in the Sphinx usage guide.
- Verify every package source/resource file and the installed console entry point in built distributions.
- Rename the distribution to `fastapi-logging-kit` and the import namespace to `fastapi_logging_kit`.
- Rename the CLI command, environment-variable prefix, LogiBoard static URL, and project documentation links to match the new package identity.
- Raise the minimum supported Python version to 3.11 and cap the declared range at Python 3.15 until the next compatibility cycle.
- Drop Python 3.9 and 3.10 from the supported runtime and CI matrices.
- Declare runtime and optional dependencies through PEP 621 metadata and use SPDX license metadata.
- Keep tests, documentation, and development support files in the source distribution while excluding tests from the wheel.
- Use Python 3.15 with the current FastAPI compatibility line in CI.
- Pin the legacy FastAPI compatibility lane to an httpx version compatible with its Starlette TestClient.
- Update test and documentation tooling to versions that support the new Python matrix.

### Fixed

- Adapt contribution, conduct, security, and release policies to FastAPI Logging Kit.
- Restore the FastAPI CI matrix and reuse it for version-checked release builds.
- Exclude internal tests from wheels while retaining source-distribution support files.
- Correct structured configuration examples and cross-platform static-check exclusions.

- Restrict log archiving to recognized rotated log filenames; unrelated files are no longer moved.
- Preserve nested log-directory paths when archiving rotated files.
- Exclude symlinked files and directories from archive discovery.
- Publish gzip archives atomically and preserve the source when compression fails.
- Avoid leaving the temporary archive base file behind when the `send-logs` command completes.
- Make LogiBoard route and static-asset installation idempotent.
- Detect LogiBoard route conflicts before changing application logging or middleware state.
- Reject asynchronous and non-boolean LogiBoard permission results instead of treating truthy coroutine objects or values as authorization.
- Reject middleware and LogiBoard registration attempts that occur after the ASGI app has started, before mutating legacy settings.
- Render uploaded ZIP filenames as text instead of HTML, preventing archive-name script injection in LogiBoard.
- Build archive folder trees with null-prototype objects to avoid prototype-key collisions.
- Pin the LogiBoard ZIP parser with Subresource Integrity.
- Align the README's LogiBoard permission example with the application-scoped API and document the authentication middleware requirement.
