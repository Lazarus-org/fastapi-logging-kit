Welcome to fastapi_logging_kit Documentation!
======================================

.. |br| raw:: html

   <br />

.. image:: https://img.shields.io/github/license/lazarus-org/fastapi-logging-kit
    :target: https://github.com/lazarus-org/fastapi-logging-kit/blob/main/LICENCE
    :alt: License

.. image:: https://img.shields.io/pypi/v/fastapi-logging-kit
    :target: https://pypi.org/project/fastapi-logging-kit/
    :alt: PyPI release

.. image:: https://img.shields.io/readthedocs/fastapi-logging-kit
    :target: https://fastapi-logging-kit.readthedocs.io/en/latest/
    :alt: Documentation

.. image:: https://img.shields.io/badge/pylint-10/10-brightgreen?logo=python&logoColor=blue
   :target: https://www.pylint.org/
   :alt: Pylint

.. image:: https://img.shields.io/pypi/pyversions/fastapi-logging-kit
    :target: https://pypi.org/project/fastapi-logging-kit/
    :alt: Supported Python versions

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

imagine you have a FastAPI service that was developed a few years ago and already uses Python's built-in ``logging``. Refactoring the entire codebase to use another logging package would be a daunting task. But with ``fastapi_logging_kit``, you don't have to worry about that. Simply install fastapi_logging_kit, call ``setup_logging(app)`` once, and enjoy all its advanced features with logging each ``LEVEL`` in separate files with three extra formats (``json``, ``xml``, ``flat``) **without having to make any changes** to your existing code.

``fastapi_logging_kit`` is a port of `django_logging <https://github.com/lazarus-org/django_logging>`_. If you are coming from that package, see :ref:`migrating_from_django_logging` for the mapping between the two.

Supported Versions
------------------

`fastapi_logging_kit` supports the following combinations of FastAPI and Python versions:

==========  ==========================================
  FastAPI     Python
==========  ==========================================
0.100+      3.9, 3.10, 3.11, 3.12, 3.13, 3.14
0.115+      3.10, 3.11, 3.12, 3.13, 3.14
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
