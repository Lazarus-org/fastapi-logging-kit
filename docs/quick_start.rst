Quick Start
===========

Getting Started with `fastapi_logging_kit` is simple. Follow these steps to get up and running quickly:

1. **Install the Package**

   first, Install `fastapi_logging_kit` via pip:

.. code-block:: shell

  $ pip install fastapi-logging-kit

2. **Call** ``setup_logging``

   FastAPI has no application registry, so there is no equivalent of Django's ``INSTALLED_APPS``. Instead, call ``setup_logging`` once, passing your application:

.. code-block:: python

  from fastapi import FastAPI

  from fastapi_logging_kit import setup_logging

  app = FastAPI()
  setup_logging(app)

That single call configures the logging, installs the request logging middleware and — if you enable it — mounts the LogiBoard router.

3. **Run Your Server**

   Start your server to verify the installation:

.. code-block:: shell

   uvicorn main:app --reload

By default, the structured integration preserves the host application's
existing root handlers and adds an INFO-level console handler for the
``fastapi_logging_kit`` namespace. Request-completion records are emitted by the
installed middleware. This default does **not** print a legacy initialization
summary, create per-level log files, or install ``MonitorLogSizeMiddleware``.

If you need per-level files, rotation, email alerts, and the weekly log-size
audit, use the documented legacy flat-key configuration or configure the
handlers you need through the structured ``LOGGING``/``COMPONENTS`` contract.

That's it! `fastapi_logging_kit` is ready to use. For further customization, refer to the :doc:`Settings <settings>`.
