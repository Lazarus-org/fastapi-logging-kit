FastAPI Logging Kit Documentation
======================================

.. |br| raw:: html

   <br />

.. image:: https://img.shields.io/github/license/lazarus-org/fastapi-logging-kit
    :target: https://github.com/lazarus-org/fastapi-logging-kit/blob/main/LICENCE
    :alt: License

.. image:: https://img.shields.io/readthedocs/fastapi-logging-kit
    :target: https://fastapi-logging-kit.readthedocs.io/en/latest/
    :alt: Documentation

.. image:: https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=yellow
   :target: https://github.com/pre-commit/pre-commit
   :alt: pre-commit

.. image:: https://img.shields.io/github/issues/lazarus-org/fastapi-logging-kit
    :target: https://github.com/lazarus-org/fastapi-logging-kit/issues
    :alt: Open Issues

.. image:: https://img.shields.io/github/last-commit/lazarus-org/fastapi-logging-kit
    :target: https://github.com/lazarus-org/fastapi-logging-kit/commits/main
    :alt: Last Commit

.. image:: https://img.shields.io/github/languages/top/lazarus-org/fastapi-logging-kit
    :target: https://github.com/lazarus-org/fastapi-logging-kit
    :alt: Languages

.. image:: https://codecov.io/gh/lazarus-org/fastapi-logging-kit/branch/main/graph/badge.svg
   :target: https://codecov.io/gh/lazarus-org/fastapi-logging-kit
   :alt: Coverage

|br|

`fastapi_logging_kit` is a powerful yet simple FastAPI package that extends and enhances Python's built-in ``logging`` without relying on any **third-party** logging libraries. Our goal is to keep things straightforward while providing flexible and customizable logging solutions that are specifically designed for FastAPI applications.

One of the key advantages of ``fastapi_logging_kit`` is its seamless integration. Get started with fastapi_logging_kit in your existing projects without refactoring any code. Even if you're already using the **built-in logging module**, you can instantly upgrade to advanced features with just a simple installation. No extra changes or complicated setup required!

Imagine you have a FastAPI service that already uses Python's built-in ``logging``. Refactoring the entire codebase to use another logging package would be a daunting task. With ``fastapi_logging_kit``, you can integrate request logging and console output by calling ``setup_logging(app)``. Configure file handlers and the JSON, XML, or FLAT formats explicitly when you need them; the default setup does not silently replace your existing root handlers.

``fastapi_logging_kit`` is a port of `django_logging <https://github.com/lazarus-org/django_logging>`_. If you are coming from that package, see :ref:`migrating_from_django_logging` for the mapping between the two.

Supported Versions
------------------

`fastapi_logging_kit` supports the following combinations of FastAPI and Python versions:

==========  ==========================================
  FastAPI     Python
==========  ==========================================
0.100+      3.11, 3.12, 3.13, 3.14
0.115+      3.11, 3.12, 3.13, 3.14, 3.15
==========  ==========================================

Documentation
-------------

The documentation is organized into the following sections:

.. toctree::
   :maxdepth: 2

   quick_start
   usage
   log_iboard
   settings
   contributing
   rules

Issues
------
If you have questions or have trouble using the app please file a bug report at:

https://github.com/lazarus-org/fastapi-logging-kit/issues


Indices and tables
==================

* :ref:`search`
* :ref:`genindex`
* :ref:`modindex`
