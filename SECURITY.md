# Security Policy

## Supported Versions

Security fixes target the latest `1.0.x` release of `fastapi-logging-kit`.
The package currently declares version `1.0.0`. Supported runtimes are Python
3.11-3.15, as declared in `pyproject.toml` and the CI matrix.

| Version | Supported |
| --- | --- |
| Latest 1.0.x | Security fixes supported |

## Reporting a Vulnerability

We take security issues seriously. If you find a vulnerability in `fastapi_logging_kit`, please report it confidentially. Here are the steps to report security vulnerabilities:

1. **Email**: Please send an email to [aryan513966@gmail.com](mailto:aryan513966@gmail.com) with a detailed description of the vulnerability.
2. **Details**: In your email, include the following details:
   - Description of the vulnerability.
   - Potential impact and severity.
   - Steps to reproduce the issue.
   - Any other relevant information, such as proof of concept or screenshots.

We will:
- Acknowledge your report within 2 business days.
- Work with you to understand and resolve the issue as quickly as possible.
- Provide an estimate of when a patch will be available and credit you (if desired) in the changelog.

## Handling Vulnerabilities

When a vulnerability is confirmed:
- We will create a fix and apply it to all actively supported versions of `fastapi_logging_kit`.
- A new release with the security fix will be published, and the vulnerability will be disclosed in the changelog or via a security advisory.
- We may delay the disclosure of details about the vulnerability until a sufficient number of users have updated to the patched version.

## General Security Guidelines

- Keep your `fastapi_logging_kit` package up to date with the latest versions to ensure you benefit from the latest security fixes.
- Follow our changelog for announcements regarding security fixes.
- Ensure that your logging configuration is secure and does not expose sensitive information in log files.
- When using log rotation with compression (`COMPRESS: True`), ensure your archive directory has appropriate filesystem permissions to prevent unauthorized access to rotated log files.

## Responsible Disclosure

We strongly encourage responsible disclosure and will work to fix issues in a timely manner. We appreciate any effort to help make `fastapi_logging_kit` more secure for all users.

Thank you for helping us improve the security of `fastapi_logging_kit`!


## Deployment guidance

- LogiBoard authorization is application-specific. Install authentication before
  relying on `scope["user"]`, and use a synchronous permission callback returning
  a real boolean. Packaged CSS and JavaScript are public static assets.
- Query strings, JSON bodies, and SQL logging can expose sensitive data. Enable
  them explicitly, configure field exclusions and size limits, and avoid secrets
  in free-text messages; structured redaction cannot sanitize arbitrary text.
- Trust forwarding headers only from explicitly configured `TRUSTED_PROXIES`.
- Protect log and archive directories with appropriate filesystem permissions.
  Standard rotating file handlers are not safe for concurrent processes writing
  the same file. Prefer stdout collection or external rotation for worker pools.
- SMTP notifications use bounded background workers and timeouts. They are
  best-effort, not a durable queue; shutdown or exhausted capacity may lose mail.
