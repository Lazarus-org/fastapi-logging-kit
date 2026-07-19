Quick Start
===========

Getting Started with `fast_logging` is simple. Follow these steps to get up and running quickly:

1. **Install the Package**

   first, Install `fast_logging` via pip:

.. code-block:: shell

  $ pip install fast-logging

2. **Call** ``setup_logging``

   FastAPI has no application registry, so there is no equivalent of Django's ``INSTALLED_APPS``. Instead, call ``setup_logging`` once, passing your application:

.. code-block:: python

  from fastapi import FastAPI

  from fast_logging import setup_logging

  app = FastAPI()
  setup_logging(app)

That single call configures the logging, installs the request logging middleware and — if you enable it — mounts the LogiBoard router.

3. **Run Your Server**

   Start your server to verify the installation:

.. code-block:: shell

   uvicorn main:app --reload

when the server starts, you'll see an initialization message like this in your *console*:

.. code-block:: text

  INFO | 'datetime' | fast_logging | Logging initialized with the following configurations:
  Log File levels: ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'].
  Log files are being written to: logs.
  Console output level: DEBUG.
  Colorize console: True.
  Log date format: %Y-%m-%d %H:%M:%S.
  Email notifier enabled: False.
  Log rotation type: none.

By default, fast_logging will log each level to its own file:

- DEBUG : ``logs/debug.log``
- INFO : ``logs/info.log``
- WARNING : ``logs/warning.log``
- ERROR : ``logs/error.log``
- CRITICAL : ``logs/critical.log``

In addition, logs will be displayed in **colorized** mode in the ``console``, making it easier to distinguish between different log levels.

That's it! `fast_logging` is ready to use. For further customization, refer to the :doc:`Settings <settings>`.
