# Fast Logging

Welcome to fast_logging Documentation!

![License](https://img.shields.io/github/license/lazarus-org/fast-logging)
![PyPI release](https://img.shields.io/pypi/v/fast-logging)
![Documentation](https://img.shields.io/readthedocs/fast-logging)
![CI Workflow](https://github.com/lazarus-org/fast-logging/actions/workflows/ci.yml/badge.svg)
![Supported Python versions](https://img.shields.io/pypi/pyversions/fast-logging)
[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=yellow)](https://github.com/pre-commit/pre-commit)
![Last Commit](https://img.shields.io/github/last-commit/lazarus-org/fast-logging)
![Languages](https://img.shields.io/github/languages/top/lazarus-org/fast-logging)
![Open Issues](https://img.shields.io/github/issues/lazarus-org/fast-logging)
[![codecov](https://codecov.io/gh/lazarus-org/fast-logging/branch/main/graph/badge.svg)](https://codecov.io/gh/lazarus-org/fast-logging)
[![pylint](https://img.shields.io/badge/pylint-10/10-brightgreen?logo=python&logoColor=blue)](https://www.pylint.org/)

The [`fast_logging`](https://github.com/lazarus-org/fast-logging) is a powerful yet simple FastAPI package that extends and enhances Python's built-in ``logging`` without relying on any **third-party** logging libraries. Our goal is to keep things straightforward while providing flexible and customizable logging solutions that are specifically designed for FastAPI applications.

One of the key advantages of ``fast_logging`` is its seamless integration. Get started with fast_logging in your existing projects without refactoring any code. Even if you're already using the **built-in logging module**, you can instantly upgrade to advanced features with just a simple installation. No extra changes or complicated setup required!

imagine you have a FastAPI service that was developed a few years ago and already uses Python's built-in ``logging``. Refactoring the entire codebase to use another logging package would be a daunting task. But with ``fast_logging``, you don't have to worry about that. Simply install fast_logging, call ``setup_logging(app)`` once, and enjoy all its advanced features with logging each ``LEVEL`` in separate files with three extra formats (``json``, ``xml``, ``flat``) **without having to make any changes** to your existing code.

`fast_logging` is a port of [`django_logging`](https://github.com/lazarus-org/django_logging). If you are coming from that package, see [Migrating from django_logging](#migrating-from-django_logging) for the mapping between the two.


## Project Detail

- Language: Python >= 3.9
- Framework: FastAPI >= 0.100


## Documentation

The documentation is organized into the following sections:

- [Quick Start](#quick-start)
- [Usage](#usage)
- [LogiBoard Integration](#logiboard-integration)
- [Settings](#settings)
- [Log Rotation](#log-rotation)
- [CLI Commands](#cli-commands)
- [Available Format Options](#available-format-options)
- [Required Email Settings](#required-email-settings)
- [Migrating from django_logging](#migrating-from-django_logging)


## Quick Start

Getting started with `fast_logging` is simple. Follow these steps to get up and running quickly:

1. **Install the Package**

first, Install `fast_logging` via pip:

```shell
$ pip install fast-logging
```

2. **Call `setup_logging`**

FastAPI has no application registry, so there is no equivalent of Django's `INSTALLED_APPS`. Instead, call `setup_logging` once, passing your application:

```python
from fastapi import FastAPI

from fast_logging import setup_logging

app = FastAPI()
setup_logging(app)
```

That single call configures the logging, installs the request logging middleware and — if you enable it — mounts the LogiBoard router.

3. **Run Your Server**

Start your server to verify the installation:

```shell
uvicorn main:app --reload
```

when the server starts, you'll see an initialization message like this in your *console*:

```shell
INFO | 'datetime' | fast_logging | Logging initialized with the following configurations:
Log File levels: ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'].
Log files are being written to: logs.
Console output level: DEBUG.
Colorize console: True.
Log date format: %Y-%m-%d %H:%M:%S.
Email notifier enabled: False.
Log rotation type: none.
```

By default, fast_logging will log each level to its own file:
- DEBUG : `logs/debug.log`
- INFO : `logs/info.log`
- WARNING : `logs/warning.log`
- ERROR : `logs/error.log`
- CRITICAL : `logs/critical.log`

In addition, logs will be displayed in ***colorized*** mode in the `console`, making it easier to distinguish between different log levels.

That's it! `fast_logging` is ready to use. For further customization, refer to the [Settings](#settings) section.


## Usage

Once `fast_logging` is installed and `setup_logging` has been called, you can start using it right away. The package provides several features to customize and enhance logging in your FastAPI project. Below is a guide on how to use the various features provided by `fast_logging`.

### Basic Logging Usage:

At its core, `fast_logging` is built on top of Python's built-in logging module. This means you can use the standard logging module to log messages across your project. Here's a basic example of logging usage:

```python
import logging

logger = logging.getLogger(__name__)

logger.debug("This is a debug message")
logger.info("This is an info message")
logger.warning("This is a warning message")
logger.error("This is an error message")
logger.critical("This is a critical message")
```

These logs will be handled according to the configurations set up by `fast_logging`, using either the default settings or any custom settings you've provided.

### Configuring

`setup_logging` accepts the configuration as its second argument:

```python
from fastapi import FastAPI

from fast_logging import setup_logging

app = FastAPI()

setup_logging(
    app,
    {
        "LOG_DIR": "logs",
        "LOG_FILE_LEVELS": ["INFO", "ERROR", "CRITICAL"],
        "LOG_FILE_FORMAT_TYPES": {"ERROR": "JSON"},
    },
)
```

Every option can also be supplied through the environment, using the `FAST_LOGGING_` prefix. Values are parsed as JSON, falling back to a plain string:

```shell
export FAST_LOGGING_LOG_DIR=/var/log/myapp
export FAST_LOGGING_LOG_FILE_LEVELS='["INFO", "ERROR"]'
export FAST_LOGGING_LOG_CONSOLE_COLORIZE=false
```

An explicit mapping passed to `setup_logging` takes priority over the environment, which in turn takes priority over the packaged defaults. This means the CLI commands pick up the same `FAST_LOGGING_LOG_DIR` your application uses, with no extra wiring.

`setup_logging` can also be called without an application when you only want the logging configured — for example in a worker process or a maintenance script:

```python
from fast_logging import setup_logging

setup_logging(config={"LOG_DIR": "logs"})
```

### Context Manager:

You can use the `config_setup` context manager to temporarily apply `fast_logging` configurations within a specific block of code.
Example usage:

```python
import logging

from fast_logging.utils.context_manager import config_setup

logger = logging.getLogger(__name__)


def foo():
    logger.info("This log will use the configuration set in the context manager!")


with config_setup():
    """Your logging configuration changes here"""
    foo()

# the logging configuration will restore to what it was before, in here outside of with block
```

- Note: `AUTO_INITIALIZATION_ENABLE` must be set to `False` in the configuration to use the context manager. If it is `True`, attempting to use the context manager will raise a `ValueError`.

### Log and Notify Utility:

To send specific logs as email, use the `log_and_notify_admin` function. Ensure that the `ENABLE` option in `LOG_EMAIL_NOTIFIER` is set to `True` in your configuration:

```python
import logging

from fast_logging.utils.log_email_notifier.log_and_notify import log_and_notify_admin

logger = logging.getLogger(__name__)

log_and_notify_admin(logger, logging.INFO, "This is a log message")
```

You can also include request details in the email by passing the request through `extra`:

```python
log_and_notify_admin(
    logger,
    logging.INFO,
    "This is a log message",
    extra={"request": request},
)
```

- **Note**: To use this feature, the `EMAIL` settings must be configured. see [Required Email Settings](#required-email-settings).

### Execution Tracker Decorator:

The `execution_tracker` decorator logs the execution time and, optionally, the number of database queries for a function:

```python
import logging

from fast_logging.decorators import execution_tracker

logger = logging.getLogger(__name__)


@execution_tracker(
    logging_level=logging.INFO,
    log_queries=True,
    query_threshold=10,
    query_exceed_warning=True,
)
def some_function():
    # function code
    pass
```

**Arguments**:

- `logging_level` (`int`): the level at which the metrics are logged. Defaults to `logging.INFO`.
- `log_queries` (`bool`): whether to include the number of database queries. Requires `DEBUG` to be `True` in your configuration. Defaults to `False`.
- `query_threshold` (`int | None`): logs a warning when the query count exceeds this number. Defaults to `None`.
- `query_exceed_warning` (`bool`): whether to emit that warning. Defaults to `False`.

**Tracking queries**

Django counted queries automatically through `connection.queries`. FastAPI ships no ORM, so `fast_logging` keeps its own per-context query log. If you use SQLAlchemy, instrument your engine once at startup:

```python
from sqlalchemy import create_engine

from fast_logging import instrument_sqlalchemy

engine = create_engine("postgresql://...")
instrument_sqlalchemy(engine)
```

Using a different database library? Report queries yourself from your own instrumentation:

```python
from fast_logging import record_query

record_query("SELECT * FROM users", duration=0.014)
```

### Request Logging Middleware:

`RequestLogMiddleware` is installed for you by `setup_logging`. To install it yourself — for example to control the middleware ordering — add it directly:

```python
from fastapi import FastAPI

from fast_logging import RequestLogMiddleware, setup_logging

app = FastAPI()
setup_logging(app, add_middleware=False)
app.add_middleware(RequestLogMiddleware)
```

#### Key Features

- **Request/response logging**: logs the method, path, query parameters and referrer when a request starts, and the user, status code, content type and elapsed time when it finishes.
- **Request IDs**: reuses an incoming `X-Request-ID` header when present, otherwise generates a UUID.
- **Context propagation**: binds `request_id`, `ip_address` and `user_agent` to the context variables, so every log record emitted while handling the request carries them automatically.
- **Streaming support**: emits `Streaming started` and `Streaming finished` records around streaming responses.
- **Cancellation handling**: logs a warning and releases the bound context when a client disconnects mid-request.
- **SQL query logging**: includes the queries a request issued when `LOG_SQL_QUERIES_ENABLE` is on.

The middleware is pure ASGI, so it forwards websocket and lifespan traffic untouched.

Example output:

```
INFO | 2026-01-05 12:00:00 | request_middleware | REQUEST STARTED:
	method=GET
	path=/api/items
	query_params={'page': '2'}
	referrer=None
 | {'request_id': 'a3f1...', 'ip_address': '10.0.0.4', 'user_agent': 'curl/8.4.0'}

INFO | 2026-01-05 12:00:00 | request_middleware | REQUEST FINISHED:
	user=Anonymous
	status_code=200
	content_type=[application/json]
	response_time=[0.02 second(s)]
 | {'request_id': 'a3f1...', 'ip_address': '10.0.0.4', 'user_agent': 'curl/8.4.0'}
```

#### Identifying the user

FastAPI has no built-in authentication, so the middleware reads the user from `scope["user"]` — the convention used by Starlette's `AuthenticationMiddleware` and most FastAPI auth extensions. When no user is present, requests are logged as `Anonymous`.

#### Context Variables Usage

Because the request context is bound to context variables, your own log calls inherit it without you passing anything:

```python
import logging

logger = logging.getLogger(__name__)


@app.get("/items")
async def list_items():
    logger.info("Listing items")  # automatically carries request_id, ip_address, user_agent
    return []
```

### MonitorLogSizeMiddleware

`MonitorLogSizeMiddleware` runs the log size audit at most once a week, warning the admin by email when the log directory exceeds `LOG_DIR_SIZE_LIMIT`. It is installed by `setup_logging` alongside the request middleware.

The "last run" timestamp is kept in a small in-process cache. If you run several workers and want them to share it, install your own backend:

```python
from fast_logging import set_cache

set_cache(my_redis_backed_cache)  # any object with .get(key, default) and .set(key, value, timeout)
```

- **Note**: this feature requires the `EMAIL` settings to be configured. see [Required Email Settings](#required-email-settings).

### Context Variable Management

`fast_logging` exposes the context manager used internally, so you can attach your own fields to every log record in a block of code.

#### Binding and Unbinding Context Variables

```python
import logging

from fast_logging import manager

logger = logging.getLogger(__name__)

# Binding context variables
manager.bind(user_id=42, tenant="acme")
logger.info("Processing")  # context: {'user_id': 42, 'tenant': 'acme'}

# Unbinding a single variable
manager.unbind("tenant")
logger.info("Still processing")  # context: {'user_id': 42}

# Clearing everything
manager.clear()
```

#### Batch Binding and Resetting Context Variables

`batch_bind` returns tokens you can use to restore the previous values:

```python
from fast_logging import manager

tokens = manager.batch_bind(request_id="abc", stage="validate")
try:
    ...
finally:
    manager.reset(tokens)
```

#### Retrieving and Merging Context Variables

```python
from fast_logging import manager

manager.get_contextvars()  # {'request_id': 'abc'}
manager.get_merged_context({"extra": "value"})  # bound logger context wins over ambient
```

#### Scoped Context Management

The cleanest option is `scoped_context`, which binds for the duration of a block and restores afterwards — even if the block raises:

```python
from fast_logging import manager

with manager.scoped_context(job_id="import-42"):
    run_import()  # every log record inside carries job_id
```


## LogiBoard Integration

LogiBoard lets you upload and browse log files in the browser.

### Setup Instructions

1. Enable it in your configuration:

```python
setup_logging(app, {"INCLUDE_LOG_iBOARD": True})
```

That registers the page at `/log-iboard/` and mounts its assets at `/fast-logging/static`.

2. Restrict access.

FastAPI has no permission framework, so access is controlled by a predicate you can replace. The default reads `is_superuser` from `scope["user"]` and **denies anonymous requests**, which matches how Django's `AnonymousUser` failed the same check. Install your own rule with `set_permission_check`:

```python
from fast_logging.routers import set_permission_check


def only_admins(request) -> bool:
    user = request.scope.get("user")
    return bool(user and user.role == "admin")


set_permission_check(only_admins)
```

Users failing the check are shown an "Access Denied" page with a `403` status.

### Using LogiBoard

Visit `/log-iboard/` and upload a `.zip` of your logs. LogiBoard renders the directory tree and previews `JSON`, `XML` and `txt` files in the browser.


## Settings

By default, `fast_logging` uses a built-in configuration that requires no additional setup. However, you can customize the logging settings by passing a configuration mapping to `setup_logging`, or by setting `FAST_LOGGING_`-prefixed environment variables.

#### Default configuration:

```python
{
    "AUTO_INITIALIZATION_ENABLE": True,
    "INITIALIZATION_MESSAGE_ENABLE": True,
    "LOG_SQL_QUERIES_ENABLE": False,
    "LOG_FILE_LEVELS": ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
    "LOG_DIR": "logs",
    "LOG_DIR_SIZE_LIMIT": 1024,  # MB
    "LOG_FILE_FORMATS": {
        "DEBUG": 1,
        "INFO": 1,
        "WARNING": 1,
        "ERROR": 1,
        "CRITICAL": 1,
    },
    "LOG_FILE_FORMAT_TYPES": {
        "DEBUG": "normal",
        "INFO": "normal",
        "WARNING": "normal",
        "ERROR": "normal",
        "CRITICAL": "normal",
    },
    "EXTRA_LOG_FILES": {
        "DEBUG": False,
        "INFO": False,
        "WARNING": False,
        "ERROR": False,
        "CRITICAL": False,
    },
    "LOG_CONSOLE_LEVEL": "DEBUG",
    "LOG_CONSOLE_FORMAT": 1,
    "LOG_CONSOLE_COLORIZE": True,
    "LOG_DATE_FORMAT": "%Y-%m-%d %H:%M:%S",
    "LOG_EMAIL_NOTIFIER": {
        "ENABLE": False,
        "NOTIFY_ERROR": False,
        "NOTIFY_CRITICAL": False,
        "LOG_FORMAT": 1,
        "USE_TEMPLATE": True,
    },
    "INCLUDE_LOG_iBOARD": False,
    "DEBUG": False,
    "EMAIL": {},
    # Rotation (all optional — defaults to no rotation)
    "LOG_ROTATION": {
        "TYPE": "none",
        "MAX_BYTES": 10485760,  # 10 MB
        "BACKUP_COUNT": 5,
        "WHEN": "midnight",
        "INTERVAL": 1,
        "COMPRESS": False,
    },
    "LOG_ROTATION_OVERRIDES": {},
}
```

#### Configuration Options:

Here's a breakdown of the available configuration options:

`AUTO_INITIALIZATION_ENABLE`
----------------------------

- **Type**: `bool`
- **Description**: Enables automatic initialization of logging configurations.
- **Default**: `True`

`INITIALIZATION_MESSAGE_ENABLE`
-------------------------------

- **Type**: `bool`
- **Description**: Enables logging of the initialization message when logging starts.
- **Default**: `True`

`INCLUDE_LOG_iBOARD`
--------------------

- **Type**: `bool`
- **Description**: Registers the LogiBoard route and static files on your application. For setting up LogiBoard, please refer to [LogiBoard Integration](#logiboard-integration).
- **Default**: `False`

`LOG_SQL_QUERIES_ENABLE`
------------------------

- **Type**: `bool`
- **Description**: Enables logging of SQL queries within `RequestLogMiddleware` logs. When enabled, queries recorded during each request will be included in the log output. See [Tracking queries](#execution-tracker-decorator) for how queries are collected.
- **Default**: `False`

`DEBUG`
-------

- **Type**: `bool`
- **Description**: Replaces Django's `settings.DEBUG`. Gates query counting in the `execution_tracker` decorator.
- **Default**: `False`

`LOG_FILE_LEVELS`
-----------------

- **Type**: `list[str]`
- **Description**: Specifies which log levels should be captured in log files.
- **Default**: `["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]`

`LOG_DIR`
---------

- **Type**: `str`
- **Description**: Specifies the directory where log files will be stored.
- **Default**: `"logs"`

`LOG_DIR_SIZE_LIMIT`
--------------------

- **Type**: `int`
- **Description**: Specifies the maximum allowed size of the log directory in megabytes (MB). If the directory exceeds this limit and `MonitorLogSizeMiddleware` is enabled, a warning email will be sent to the admin weekly.
- **Default**: `1024 MB` (1 GB)

`LOG_FILE_FORMATS`
------------------

- **Type**: `dict[str, int | str]`
- **Description**: Maps each log level to its corresponding log format. The format can be an `int` referencing a predefined format or a custom `str` format.
- **Default**: Format `1` for all levels.
- **Note**: See the [Available Format Options](#available-format-options) below for available formats.

`LOG_FILE_FORMAT_TYPES`
-----------------------

- **Type**: `dict[str, str]`
- **Description**: Defines the format type (e.g., `normal`, `JSON`, `XML`, `FLAT`) for each log level. The keys are log levels, and the values are the format types.
    - **Format Types**:

      - ``normal``: Standard text log.
      - ``JSON``: Structured logs in JSON format.
      - ``XML``: Structured logs in XML format.
      - ``FLAT``: logs with Flat format.

- **Default**: Type `normal` for all levels.

`EXTRA_LOG_FILES`
-----------------

- **Type**: `dict[str, bool]`
- **Description**: Determines whether separate log files for `JSON` or `XML` formats should be created for each log level. When set to `True` for a specific level, a dedicated directory (e.g., `logs/json` or `logs/xml`) will be created with files like `info.json` or `info.xml`. If `False`, json and xml logs will be written to `.log` files.
- **Default**: `False` for all levels.

`LOG_CONSOLE_LEVEL`
-------------------

- **Type**: `str`
- **Description**: Specifies the log level for console output.
- **Default**: `"DEBUG"`

`LOG_CONSOLE_FORMAT`
--------------------

- **Type**: `int | str`
- **Description**: Specifies the format for console logs, similar to `LOG_FILE_FORMATS`.
- **Default**: format option `1`

`LOG_CONSOLE_COLORIZE`
----------------------

- **Type**: `bool`
- **Description**: Determines whether console output should be colorized.
- **Default**: `True`

`LOG_DATE_FORMAT`
-----------------

- **Type**: `str`
- **Description**: Specifies the date format for log messages.
- **Default**: `"%Y-%m-%d %H:%M:%S"`

`LOG_EMAIL_NOTIFIER`
--------------------

- **Type**: `dict`
- **Description**: Configures the email notifier for sending log-related alerts.

    - `ENABLE`:
      - **Type**: `bool`
      - **Description**: Enables or disables the email notifier.
      - **Default**: `False`

    - `NOTIFY_ERROR`:
      - **Type**: `bool`
      - **Description**: Sends an email when an `ERROR` record is logged.
      - **Default**: `False`

    - `NOTIFY_CRITICAL`:
      - **Type**: `bool`
      - **Description**: Sends an email when a `CRITICAL` record is logged.
      - **Default**: `False`

    - `LOG_FORMAT`:
      - **Type**: `int | str`
      - **Description**: The format used for the log message in the email.
      - **Default**: `1`

    - `USE_TEMPLATE`:
      - **Type**: `bool`
      - **Description**: Whether the email body is rendered with the packaged HTML template.
      - **Default**: `True`

`EMAIL`
-------

- **Type**: `dict`
- **Description**: The SMTP settings used to deliver notifications. In `django_logging` these were top-level Django settings; here they are namespaced under this key. See [Required Email Settings](#required-email-settings).
- **Default**: `{}`


## Log Rotation

By default `fast_logging` writes to plain files that grow forever. Rotation is opt-in through `LOG_ROTATION`, and can be overridden per level with `LOG_ROTATION_OVERRIDES`.

`LOG_ROTATION`
--------------

- **Type**: `dict`

    - `TYPE`:
      - **Type**: `str`
      - **Description**: One of `"none"` (a plain `FileHandler`), `"size"` (a `RotatingFileHandler`) or `"time"` (a `TimedRotatingFileHandler`).
      - **Default**: `"none"`

    - `MAX_BYTES`:
      - **Type**: `int`
      - **Description**: The size at which a file is rotated. Used when `TYPE` is `"size"`.
      - **Default**: `10485760` (10 MB)

    - `BACKUP_COUNT`:
      - **Type**: `int`
      - **Description**: How many rotated files to keep. `0` keeps all of them.
      - **Default**: `5`

    - `WHEN`:
      - **Type**: `str`
      - **Description**: The rotation interval unit. Used when `TYPE` is `"time"`. One of `s`, `m`, `h`, `d`, `midnight`, or `w0`–`w6`.
      - **Default**: `"midnight"`

    - `INTERVAL`:
      - **Type**: `int`
      - **Description**: How many `WHEN` units between rotations.
      - **Default**: `1`

    - `COMPRESS`:
      - **Type**: `bool`
      - **Description**: Whether rotated files are gzipped.
      - **Default**: `False`

`LOG_ROTATION_OVERRIDES`
------------------------

- **Type**: `dict[str, dict]`
- **Description**: Per-level rotation settings, shallow-merged over `LOG_ROTATION`, so you only specify the keys that differ.
- **Default**: `{}`

Example — rotate everything nightly, but rotate the noisy debug log by size and compress it:

```python
setup_logging(
    app,
    {
        "LOG_ROTATION": {
            "TYPE": "time",
            "WHEN": "midnight",
            "BACKUP_COUNT": 14,
        },
        "LOG_ROTATION_OVERRIDES": {
            "DEBUG": {
                "TYPE": "size",
                "MAX_BYTES": 5242880,  # 5 MB
                "BACKUP_COUNT": 3,
                "COMPRESS": True,
            },
        },
    },
)
```


## CLI Commands

FastAPI projects have no `manage.py`, so the commands ship as a `fast-logging` console script. Every command reads the same configuration your application does, so `FAST_LOGGING_LOG_DIR` applies here too:

```shell
$ fast-logging --help
```

### send-logs

Zips the log directory and emails it to the given address.

```shell
$ fast-logging send-logs ops@example.com
```

#### Key Features:

- Compresses the entire log directory into a single zip archive.
- Attaches the archive to an email and delivers it over SMTP.
- Cleans up the temporary archive afterwards, whether or not the send succeeded.

- **Note**: requires the `EMAIL` settings. see [Required Email Settings](#required-email-settings).

### logs-size-audit

Reports the size of the log directory, broken down by category, and emails the admin when it exceeds `LOG_DIR_SIZE_LIMIT`.

```shell
$ fast-logging logs-size-audit
```

#### Example:

```
Log directory size breakdown:
  active            5 file(s)      12.40 MB
  rotated          14 file(s)     201.88 MB
  archived          3 file(s)      44.10 MB
  compressed        7 file(s)      18.02 MB
  TOTAL                           276.40 MB

Log directory size is under the limit: 276.4 MB
```

### rotate-logs

Immediately rotates every active rotating handler. Useful in a deploy script, so a new process starts on fresh files.

```shell
$ fast-logging rotate-logs
```

Plain `FileHandler` instances cannot be rotated programmatically; they are reported as skipped rather than failing.

### archive-logs

Moves rotated (non-active) log files into a timestamped `archive/` subdirectory, optionally compressing them.

```shell
# Basic — move rotated files into archive/
$ fast-logging archive-logs

# Gzip each file before moving
$ fast-logging archive-logs --compress

# Bundle the archive directory into a tar.gz and remove it
$ fast-logging archive-logs --bundle tar.gz

# Bundle into a zip file
$ fast-logging archive-logs --bundle zip

# Compress individual files and then bundle into tar.gz
$ fast-logging archive-logs --compress --bundle tar.gz

# Preview everything without touching any files
$ fast-logging archive-logs --dry-run
```

#### Arguments:

- `--compress`: gzip each uncompressed rotated file before archiving.
- `--bundle FORMAT`: bundle the archive directory into a single `tar.gz` or `zip` and remove the directory.
- `--dry-run`: print what would happen without touching any files.

Active `<level>.log` files are never touched.

### generate-pretty-json

Finds the `.json` files in `logs/json/` and rewrites them as valid, pretty-printed JSON arrays under `logs/json/pretty/`.

```shell
$ fast-logging generate-pretty-json
```

### generate-pretty-xml

Finds the `.xml` files in `logs/xml/` and wraps their contents in a single `<logs>` element under `logs/xml/pretty/`.

```shell
$ fast-logging generate-pretty-xml
```


## Available Format Options

The `fast_logging` package provides predefined log format options that you can use in configuration. You can reference these formats by their corresponding **integer keys**.

```
1.  "%(levelname)s | %(asctime)s | %(module)s | %(message)s | %(context)s"
2.  "%(levelname)s | %(asctime)s | %(context)s | %(message)s | %(exc_text)s"
3.  "%(levelname)s | %(context)s | %(message)s | %(stack_info)s"
4.  "%(context)s | %(asctime)s - %(name)s - %(levelname)s - %(message)s"
5.  "%(levelname)s | %(message)s | %(context)s | [in %(pathname)s:%(lineno)d]"
6.  "%(asctime)s | %(context)s | %(levelname)s | %(message)s | %(exc_info)s"
7.  "%(levelname)s | %(asctime)s | %(context)s | in %(module)s: %(message)s"
8.  "%(levelname)s | %(context)s | %(message)s | [%(filename)s:%(lineno)d]"
9.  "[%(asctime)s] | %(levelname)s | %(context)s | in %(module)s: %(message)s"
10. "%(asctime)s | %(processName)s | %(context)s | %(name)s | %(levelname)s | %(message)s"
11. "%(asctime)s | %(context)s | %(threadName)s | %(name)s | %(levelname)s | %(message)s"
12. "%(levelname)s | [%(asctime)s] | %(context)s | (%(filename)s:%(lineno)d) | %(message)s"
13. "%(levelname)s | [%(asctime)s] | %(context)s | {%(name)s} | (%(filename)s:%(lineno)d): %(message)s"
14. "[%(asctime)s] | %(levelname)s | %(context)s | %(name)s | %(module)s | %(message)s"
15. "%(levelname)s | %(context)s | %(asctime)s | %(filename)s:%(lineno)d | %(message)s"
16. "%(levelname)s | %(context)s | %(message)s | [%(asctime)s] | %(module)s"
17. "%(levelname)s | %(context)s | [%(asctime)s] | %(process)d | %(message)s"
18. "%(levelname)s | %(context)s | %(asctime)s | %(name)s | %(message)s"
19. "%(levelname)s | %(asctime)s | %(context)s | %(module)s:%(lineno)d | %(message)s"
20. "[%(asctime)s] | %(levelname)s | %(context)s | %(thread)d | %(message)s"
```

You can also pass a custom format string instead of an integer.


## Required Email Settings

To use the email notifier, the following settings must be configured under the `EMAIL` key:

```python
setup_logging(
    app,
    {
        "LOG_EMAIL_NOTIFIER": {"ENABLE": True, "NOTIFY_ERROR": True},
        "EMAIL": {
            "EMAIL_HOST": "smtp.example.com",
            "EMAIL_PORT": 587,
            "EMAIL_HOST_USER": "your-email@example.com",
            "EMAIL_HOST_PASSWORD": "your-email-password",
            "EMAIL_USE_TLS": True,
            "DEFAULT_FROM_EMAIL": "your-email@example.com",
            "ADMIN_EMAIL": "admin@example.com",
        },
    },
)
```

These settings ensure that the email notifier is correctly configured to send log notifications to the specified `ADMIN_EMAIL` address.

Keep credentials out of your source tree by supplying them through the environment instead:

```shell
export FAST_LOGGING_EMAIL='{"EMAIL_HOST":"smtp.example.com","EMAIL_PORT":587,"ADMIN_EMAIL":"admin@example.com"}'
```


## Migrating from django_logging

`fast_logging` keeps the same configuration keys, formats and behaviour. What changes is how the package attaches to your application:

| django_logging | fast_logging |
| --- | --- |
| Add `"django_logging"` to `INSTALLED_APPS` | Call `setup_logging(app)` |
| `DJANGO_LOGGING = {...}` in settings | A mapping passed to `setup_logging`, or `FAST_LOGGING_*` env vars |
| Top-level `EMAIL_HOST`, `ADMIN_EMAIL`, … settings | The `EMAIL` configuration key |
| `settings.DEBUG` | The `DEBUG` configuration key |
| `MIDDLEWARE` list entries | Installed by `setup_logging`, or `app.add_middleware(...)` |
| `python manage.py send_logs` | `fast-logging send-logs` |
| Django system checks abort startup | Check failures are logged as warnings; the app still boots |
| `connection.queries` | `instrument_sqlalchemy(engine)` or `record_query(...)` |
| `request.user` | `scope["user"]` |
| LogiBoard superuser check | A replaceable predicate via `set_permission_check` |
| `django.core.cache` | An in-process cache, replaceable via `set_cache` |

The formatters, filters, context variable manager, rotation handling and format options are unchanged.
