Component Extensibility
=======================

FastAPI Logging Kit builds its default handlers, formatters and filters from a set of
package presets. Applications can extend those presets through the
``FASTAPI_LOGGING["COMPONENTS"]`` mapping without editing package internals.

The extension compiler validates names and references before it creates or
attaches handlers. A component is never silently overwritten: use ``replace``
for an intentional replacement and ``disable`` to remove a preset.

Adding components
-----------------

.. code-block:: python

   FASTAPI_LOGGING = {
       "COMPONENTS": {
           "formatters": {
               "audit": {"()": "myproject.logging.AuditFormatter"},
           },
           "filters": {
               "audit_filter": {"()": "myproject.logging.AuditFilter"},
           },
           "handlers": {
               "audit_file": {
                   "class": "logging.FileHandler",
                   "filename": "logs/audit.log",
                   "level": "INFO",
                   "formatter": "audit",
                   "filters": ["audit_filter"],
               },
           },
           "loggers": {
               "myproject.audit": {
                   "handlers": ["audit_file"],
                   "level": "INFO",
                   "propagate": False,
               },
           },
       },
   }

   setup_logging(app, config=FASTAPI_LOGGING)

Component definitions use the standard ``logging.config.dictConfig`` schema.
A handler must define exactly one of ``class`` or ``()``. The latter may be a
callable or a dotted import path. Formatters and filters may likewise use the
standard ``dictConfig`` component syntax.

Routing package handlers and root handlers
------------------------------------------

``package_handlers`` attaches named handlers to the ``fastapi_logging_kit`` logger.
``root_handlers`` attaches named handlers to the root logger in ``additive``
and ``replace_root`` modes. ``isolated`` mode deliberately leaves root alone.
These are explicit routing choices; merely defining a handler does not
activate it.

.. code-block:: python

   FASTAPI_LOGGING = {
       "COMPONENTS": {
           "handlers": {
               "audit_console": {"class": "logging.StreamHandler"},
           },
           "package_handlers": ["audit_console"],
       },
   }

In the default ``additive`` setup mode, FastAPI Logging Kit preserves existing root
handlers. Its own console handler remains on the ``fastapi_logging_kit`` namespace,
while package file/email handlers are added to root. This prevents duplicate
writes and allows host handlers (including test capture handlers) to continue
receiving package log records.

In ``isolated`` mode, package handlers are routed to the ``fastapi_logging_kit``
namespace without attaching them to root. The ``replace_root`` mode applies
the generated configuration through Python's global ``dictConfig`` behavior
and is retained for compatibility with callers that explicitly want root
replacement.

Replacing or disabling presets
------------------------------

Use ``replace`` to replace an existing preset by name:

.. code-block:: python

   FASTAPI_LOGGING = {
       "COMPONENTS": {
           "replace": {
               "handlers": {
                   "info": {
                       "class": "logging.handlers.RotatingFileHandler",
                       "filename": "logs/info.log",
                       "maxBytes": 10_485_760,
                       "backupCount": 5,
                       "formatter": "info",
                       "level": "INFO",
                       "filters": ["info", "context_var_filter"],
                   },
               },
           },
           "disable": {"handlers": ["debug"]},
       },
   }

A replacement must target an existing component. Disabled handlers are removed from preset root/logger references. Disabled
filters are removed from handler/logger filter lists, and disabled formatters
are detached from handlers, so the compiled configuration does not retain
dangling references.

Validation and activation safety
--------------------------------

The component compiler rejects:

* duplicate or empty names;
* additions that collide with an existing name;
* replacements or removals for names that do not exist;
* references to missing handlers, formatters or filters;
* invalid root/package handler routes;
* attempts to replace the package-managed ``fastapi_logging_kit`` or ``root`` logger
  through the named ``loggers`` extension.

Only components reachable from active routing are instantiated. For example,
a declared but unattached file handler does not open a file. Handler-to-handler
dependencies such as ``MemoryHandler.target`` are constructed in dependency
order; unresolved references and cycles fail before the active logger graph is
changed.

Using a custom LOGGING mapping
------------------------------

The ``LOGGING`` section accepts a standard Python ``dictConfig`` mapping. When
provided, that mapping is applied as an explicit process-wide logging
configuration. It is not merged additively with the host's existing logger
graph. Set ``disable_existing_loggers`` to ``False`` when the application
expects unrelated existing loggers to remain enabled.

``COMPONENTS`` can extend or replace named components in that mapping. For a
custom ``LOGGING`` mapping, ``package_handlers`` is applied to the
``fastapi_logging_kit`` named logger and ``root_handlers`` to root.

The custom mapping and its extension are copied before compilation; callers'
input dictionaries are not mutated.
