Contributing
============

We're excited that you're interested in contributing to `fastapi_logging_kit`! Whether you're fixing a bug, adding a feature, or improving the project, your help is appreciated.

Overview
--------

- **Setting Up Your Environment**
- **Testing Your Changes**
- **Code Style Guidelines**
- **Utilizing Pre-commit Hooks**
- **Creating a Pull Request**
- **Reporting Issues**
- **Resources**

Setting Up Your Environment
---------------------------

1. **Fork the Repository:**

   Begin by forking the `fastapi-logging-kit <https://github.com/lazarus-org/fastapi-logging-kit>`_ repository on GitHub. This creates your own copy where you can make changes.

2. **Clone Your Fork:**

   Use the following command to clone your fork locally:

   .. code-block:: bash

       git clone https://github.com/your-username/fastapi-logging-kit.git
       cd fastapi-logging-kit

3. **Install Dependencies:**

   Install the necessary dependencies using ``Poetry``. If Poetry isn't installed on your machine, you can find installation instructions on the `Poetry website <https://python-poetry.org/docs/#installation>`_.

   .. code-block:: bash

       poetry install --extras sqlalchemy

4. **Create a Feature Branch:**

   It's a good practice to create a new branch for your work:

   .. code-block:: bash

       git checkout -b feature/your-feature-name

Testing Your Changes
--------------------

We use ``pytest`` for running tests. Before submitting your changes, ensure that all tests pass:

.. code-block:: bash

    poetry run pytest

The test suite is configured to require **100% coverage**, so if you're adding a new feature or fixing a bug, don't forget to write tests to cover your changes.

To verify your change across every supported Python and FastAPI combination, run the ``tox`` matrix:

.. code-block:: bash

    poetry run tox

Individual environments can be selected as well, for example:

.. code-block:: bash

    poetry run tox -e py312-fastapi0120

Code Style Guidelines
---------------------

Maintaining a consistent code style is crucial. We use ``black`` for code formatting and ``isort`` for import sorting. Make sure your code adheres to these styles:

.. code-block:: bash

    poetry run black .
    poetry run isort .

For linting, ``pylint`` is used to enforce style and catch potential errors:

.. code-block:: bash

    poetry run pylint fastapi_logging_kit

The codebase is fully type annotated and checked with ``mypy``:

.. code-block:: bash

    poetry run mypy fastapi_logging_kit

Security issues are caught with ``bandit``:

.. code-block:: bash

    poetry run bandit -c pyproject.toml -r fastapi_logging_kit

Both ``bandit`` and the pre-commit hooks are also available as dedicated ``tox`` environments:

.. code-block:: bash

    poetry run tox -e bandit
    poetry run tox -e pre-commit

Utilizing Pre-commit Hooks
--------------------------

Pre-commit hooks are used to automatically check and format code before you make a commit. This ensures consistency and quality in the codebase.

1. **Install Pre-commit:**

   ``pre-commit`` is already declared as a development dependency, so ``poetry install`` brings it in. If you need to add it explicitly:

   .. code-block:: bash

       poetry add --group dev pre-commit

2. **Set Up the Hooks:**

   Install the pre-commit hooks by running:

   .. code-block:: bash

       poetry run pre-commit install

3. **Manual Hook Execution (Optional):**

   To run all hooks manually on your codebase:

   .. code-block:: bash

       poetry run pre-commit run --all-files

Creating a Pull Request
-----------------------

Once your changes are ready, follow these steps to submit them:

1. **Commit Your Changes:**

   Write clear and concise commit messages. This project uses ``commitizen`` with the `Conventional Commits <https://www.conventionalcommits.org/en/v1.0.0/>`_ format:

   .. code-block:: bash

       git commit -am 'feat: add custom logging formatter'

   You can also let ``commitizen`` build the message for you:

   .. code-block:: bash

       poetry run cz commit

2. **Push Your Branch:**

   Push your branch to your fork on GitHub:

   .. code-block:: bash

       git push origin feature/your-feature-name

3. **Open a Pull Request:**

   Go to the original `fastapi-logging-kit <https://github.com/lazarus-org/fastapi-logging-kit>`_ repository and open a pull request. Include a detailed description of your changes and link any related issues.

4. **Respond to Feedback:**

   After submitting, a maintainer will review your pull request. Be prepared to make revisions based on their feedback.

Reporting Issues
----------------

Found a bug or have a feature request? We'd love to hear from you!

1. **Open an Issue:**

   Head over to the `Issues <https://github.com/lazarus-org/fastapi-logging-kit/issues>`_ section of the `fastapi-logging-kit` repository and click "New Issue".

2. **Describe the Problem:**

   Fill out the issue template with as much detail as possible. This helps us understand and address the issue more effectively.

Resources
---------

Here are some additional resources that might be helpful:

- `Poetry Documentation <https://python-poetry.org/docs/>`_
- `Black Documentation <https://black.readthedocs.io/en/stable/>`_
- `isort Documentation <https://pycqa.github.io/isort/>`_
- `pytest Documentation <https://docs.pytest.org/en/stable/>`_
- `pylint Documentation <https://pylint.pycqa.org/en/latest/>`_
- `mypy Documentation <https://mypy.readthedocs.io/en/stable/>`_
- `bandit Documentation <https://bandit.readthedocs.io/en/latest/>`_
- `tox Documentation <https://tox.wiki/en/latest/>`_
- `commitizen Documentation <https://commitizen-tools.github.io/commitizen/>`_
- `Pre-commit Documentation <https://pre-commit.com/>`_

----

Thank you for your interest in contributing to `fastapi_logging_kit`! We look forward to your contributions.

Repository policies and releases
--------------------------------

The repository's `contribution guide <https://github.com/lazarus-org/fastapi-logging-kit/blob/main/CONTRIBUTING.md>`_
includes pip/venv setup and maintainer release instructions. The
`Code of Conduct <https://github.com/lazarus-org/fastapi-logging-kit/blob/main/CODE_OF_CONDUCT.md>`_
sets expectations for participation. Report vulnerabilities privately using
`SECURITY.md <https://github.com/lazarus-org/fastapi-logging-kit/blob/main/SECURITY.md>`_.

Release builds check the version tag, wheel metadata and source contents, then
run the reusable CI workflow. Publishing requires the repository's
``PYPI_PUBLISH_ENABLED`` variable, a configured PyPI Trusted Publisher, and the
``pypi`` GitHub environment. Required reviewers must be configured separately
if manual approval is wanted.

Automatic version increments and publishing
-------------------------------------------

Commitizen can update the version declarations and generate release notes:

.. code-block:: bash

   poetry run cz bump --dry-run
   poetry run cz bump --changelog --check-consistency

The first command previews the version. The second updates the configured
version files, writes the changelog, and creates a local release commit and tag.
Run it only as a maintainer release step from a clean, reviewed branch.
``version_files`` keeps ``[project].version``, ``[tool.commitizen].version``, and
``fastapi_logging_kit.__version__`` aligned.

For a separate changelog commit, generate it before creating the release tag:

.. code-block:: bash

   poetry run cz changelog --incremental --unreleased-version v1.1.0
   git add CHANGELOG.md
   git commit -m "docs(changelog): prepare release 1.1.0"
   poetry run cz bump --check-consistency

Replace the example version with the version selected by the dry run. Choose
this flow or the combined ``--changelog`` flow for each release.

The complete `publishing guide <https://github.com/lazarus-org/fastapi-logging-kit/blob/main/CONTRIBUTING.md#publishing-guide>`_
covers Poetry builds, artifact validation, pushing the release tag, GitHub
Trusted Publishing, TestPyPI, and manual Poetry publishing. The same guide
retains dependency export instructions and explains how to preserve the
authoritative Poetry dependency declarations while generating optional resolved snapshots.

Dependency management and deprecation checks
--------------------------------------------

Runtime requirements live in ``[project.dependencies]`` in ``pyproject.toml``.
PEP 735 dependency groups define test, quality, documentation and build tooling;
``dev`` includes those groups. Poetry resolves them into ``poetry.lock``.
Dependabot updates this single project instead of parallel requirements files.

.. code-block:: bash

   poetry add package-name
   poetry add --group test package-name
   poetry lock
   poetry check --lock
   poetry install --extras sqlalchemy

Commit the declarations and lockfile together. Optional ``poetry export``
commands remain available for deployment snapshots; those exports are not
used by CI or Read the Docs as dependency sources.

Tests treat deprecation warnings as errors. The current compatibility lane uses
Starlette 1.10+ and HTTPX2. The legacy FastAPI lane uses older compatible HTTPX,
AnyIO and pytest releases because its Starlette TestClient still calls the
older APIs. These are dependency compatibility constraints, not warning filters.
The legacy FastAPI 0.100–0.109 lane runs on Python 3.11–3.13; Python 3.14
and 3.15 use the modern lane. Legacy FastAPI calls
``asyncio.iscoroutinefunction()``, deprecated in Python 3.14.
