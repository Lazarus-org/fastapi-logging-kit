Component Extensibility
=======================

Pass the structured ``FASTAPI_LOGGING`` mapping explicitly to
``setup_logging(app, config=FASTAPI_LOGGING)``. Its public top-level keys are
``ENABLED``, ``LOGGING``, ``COMPONENTS``, and ``REQUEST_LOGGING``. A settings
module or environment variable named ``FASTAPI_LOGGING`` is not discovered
automatically.

Adding components
-----------------

The no-config structured preset contains a ``console`` formatter, a ``console``
handler, and no preset filters or per-level file handlers. Component names must
be unique. Merely declaring a handler does not activate it; route it through a
named logger, ``package_handlers``, or ``root_handlers``.

.. code-block:: python

   from pathlib import Path
   from fastapi import FastAPI
   from fastapi_logging_kit import setup_logging

   Path("logs").mkdir(exist_ok=True)
   app = FastAPI()
   FASTAPI_LOGGING = {
       "COMPONENTS": {
           "formatters": {
               "audit": {
                   "()": "fastapi_logging_kit.formatters.JSONFormatter",
                   "fmt": "%(levelname)s %(message)s %(context)s",
                   "structured_logging": {"EXCEPTION_MODE": "type"},
               },
           },
           "filters": {
               "request_context": {
                   "()": "fastapi_logging_kit.filters.ContextVarFilter",
               },
           },
           "handlers": {
               "audit_file": {
                   "class": "logging.FileHandler",
                   "filename": "logs/audit.log",
                   "level": "INFO",
                   "formatter": "audit",
                   "filters": ["request_context"],
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

The definitions follow Python's ``logging.config.dictConfig`` syntax. A handler
requires exactly one of ``class`` or ``()``; factories may be callables or dotted
import paths. Applications create file-handler directories themselves.

Routing to package and root loggers
-----------------------------------

``package_handlers`` attaches handlers to the ``fastapi_logging_kit`` logger.
``root_handlers`` adds handlers to root while retaining existing host handlers
in the default structured setup. For example, add an audit handler to root:

.. code-block:: python

   FASTAPI_LOGGING["COMPONENTS"]["root_handlers"] = ["audit_file"]

Choose this routing before the first ``setup_logging`` call. Request middleware
configuration is copied per application, but Python's logging registry remains
process-wide. Do not attach the same output handler at multiple points in a
propagating logger chain unless duplicate output is intended.

Replacing or disabling presets
------------------------------

Use ``replace`` to change a component that already exists, and ``disable`` to
remove it. The default structured preset does not contain ``info`` or ``debug``
handlers; those belong to the legacy per-level configuration.

.. code-block:: python

   app = FastAPI()
   setup_logging(
       app,
       config={
           "COMPONENTS": {
               "replace": {
                   "formatters": {
                       "console": {
                           "()": "fastapi_logging_kit.formatters.JSONFormatter",
                           "fmt": "%(levelname)s %(message)s",
                       },
                   },
               },
           },
       },
   )

``disable`` accepts lists of existing component names, for example
``{"handlers": ["console"]}``. Disabled handlers are removed from routing;
references to disabled filters and formatters are removed as well. Disabling
the only output handler can leave the package without configured output.

Validation and activation
-------------------------

The compiler rejects missing references, duplicate names, replacement of
unknown components, and invalid routes before activation. Only components
reachable from selected routing are instantiated; an unattached file handler
does not open a file. Handler dependencies such as ``MemoryHandler.target`` are
constructed in dependency order. Activation of the default additive component
graph restores the previous logger attachments if construction or attachment
fails.

Configure before serving requests. Repeating the same structured setup on one
application is idempotent; changing its configuration after setup raises an
error. The public ``setup_logging`` function does not accept a ``mode`` keyword.

Using explicit LOGGING
----------------------

A nonempty ``LOGGING`` mapping selects Python's process-wide ``dictConfig``
replacement semantics instead of additive component activation. Existing
handlers may be replaced; setting ``disable_existing_loggers=False`` does not
preserve handlers by itself. ``COMPONENTS`` may extend this supplied mapping,
using its actual component names. Incremental dictConfig is not supported by
the structured contract.

Input mappings are copied. Application-specific middleware settings do not
isolate the global logging graph between multiple FastAPI applications.
