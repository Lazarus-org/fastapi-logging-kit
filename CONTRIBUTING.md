# Contributing to fastapi_logging_kit


We’re excited that you’re interested in contributing to `fastapi_logging_kit`! Whether you’re fixing a bug, adding a feature, or improving the project, your help is appreciated.

## Overview


- **Setting Up Your Environment**
- **Testing Your Changes**
- **Code Style Guidelines**
- **Utilizing Pre-commit Hooks**
- **Creating a Pull Request**
- **Reporting Issues**
- **Resources**
- **Automatic Version Increment with Commitizen**
- **Export Dependencies**
- **Publishing Guide**

## Setting Up Your Environment


1. **Fork the Repository:**

   Begin by forking the `fastapi_logging_kit` repository on GitHub. This creates your own copy where you can make changes.

2. **Clone Your Fork:**

   Use the following command to clone your fork locally:

   ```bash
   git clone https://github.com/your-username/fastapi-logging-kit.git
   cd fastapi-logging-kit
   ```

3. **Install Dependencies:**

   Install the necessary dependencies using `Poetry`. If Poetry isn't installed on your machine, you can find installation instructions on the [Poetry website](https://python-poetry.org/docs/#installation).

   ```bash
   poetry install --extras sqlalchemy
   ```

4. **Create a Feature Branch:**

   It’s a good practice to create a new branch for your work:

   ```bash
   git checkout -b feature/your-feature-name
   ```

## Testing Your Changes

We use `pytest` for running tests. Before submitting your changes, ensure that all tests pass:

   ```bash
   poetry run pytest
   ```

If you’re adding a new feature or fixing a bug, don’t forget to write tests to cover your changes.


## Code Style Guidelines

Maintaining a consistent code style is crucial. We use `black` for code formatting and `isort` for import sorting. Make sure your code adheres to these styles:

   ```bash
    poetry run black .
    poetry run isort .
   ```
For linting, `pylint` is used to enforce style and catch potential errors:

   ```bash
   poetry run pylint fastapi_logging_kit
   ```

## Utilizing Pre-commit Hooks

Pre-commit hooks are used to automatically check and format code before you make a commit. This ensures consistency and quality in the codebase.

1. **Install Pre-commit:**

   ```bash
   poetry add --group dev pre-commit
   ```

2. **Set Up the Hooks:**

   Install the pre-commit hooks by running:

   ```bash
   poetry run pre-commit install
   ```
3. **Manual Hook Execution (Optional):**

   To run all hooks manually on your codebase:

   ```bash
   poetry run pre-commit run --all-files
   ```

## Creating a Pull Request

Once your changes are ready, follow these steps to submit them:

1. **Commit Your Changes:**

   Write clear and concise commit messages. Following the [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/) format is recommended:

   ```bash
   git commit -am 'feat: add custom logging formatter'
   ```
2. **Push Your Branch:**

   Push your branch to your fork on GitHub:

   ```bash
   git push origin feature/your-feature-name
   ```

3. **Open a Pull Request:**

   Go to the original `fastapi_logging_kit` repository and open a pull request. Include a detailed description of your changes and link any related issues.

4. **Respond to Feedback:**

   After submitting, a maintainer will review your pull request. Be prepared to make revisions based on their feedback.

## Reporting Issues

Found a bug or have a feature request? We’d love to hear from you!

1. **Open an Issue:**

   Head over to the `Issues` section of the `fastapi_logging_kit` repository and click "New Issue".

2. **Describe the Problem:**

   Fill out the issue template with as much detail as possible. This helps us understand and address the issue more effectively.

## Resources

Here are some additional resources that might be helpful:

- [Poetry Documentation](https://python-poetry.org/docs/)
- [Black Documentation](https://black.readthedocs.io/en/stable/)
- [isort Documentation](https://pycqa.github.io/isort/)
- [pytest Documentation](https://docs.pytest.org/en/stable/)
- [pylint Documentation](https://pylint.pycqa.org/en/latest/)
- [Pre-commit Documentation](https://pre-commit.com/)

---

Thank you for your interest in contributing to `fastapi_logging_kit`! We look forward to your contributions.


## Package-specific development and validation



Use Python 3.11-3.15 and clone your fork of
[fastapi-logging-kit](https://github.com/lazarus-org/fastapi-logging-kit):

```sh
git clone https://github.com/your-username/fastapi-logging-kit.git
cd fastapi-logging-kit
python -m venv .venv
```

Activate `.venv` (`source .venv/bin/activate` on POSIX,
`.venv\Scripts\Activate.ps1` in PowerShell), then install the package and tools:

```sh
python -m pip install "poetry>=2.2,<3"
poetry install --extras sqlalchemy
git switch -c feature/your-change
```

Poetry installs dependencies directly from `pyproject.toml` and `poetry.lock`.
The `test`, `quality`, `docs`, and `build` dependency groups are combined by
`dev`. No exported requirements files or Django installation are required.

## Validation

```sh
poetry run pytest
node --test fastapi_logging_kit/tests/js/logiboard-security.test.mjs
poetry run tox -e py312-fastapi0120
poetry run mypy fastapi_logging_kit
poetry run pylint -rn -sn --rcfile=pyproject.toml fastapi_logging_kit
poetry run bandit -c pyproject.toml -r fastapi_logging_kit
poetry run sphinx-build -W --keep-going -b html docs docs/_build/html
```

Pytest enforces **100% Python statement coverage** and treats deprecation warnings
as errors. The current lane uses Starlette 1.10+ with HTTPX2; the legacy lane
uses compatible HTTPX/AnyIO/pytest versions so deprecated third-party calls do
not generate warnings. Warning suppression is not used. Run `poetry run tox` to check
all supported Python/FastAPI combinations; each environment requires its matching
interpreter. Node.js 22 or later runs the LogiBoard security tests. On restricted
systems, supply a fresh writable temporary directory with
`--basetemp=.pytest_cache/tmp-local`; pytest owns and clears that directory.

Use Black and isort for Python formatting. Install and run the existing hooks:

```sh
poetry run pre-commit install
poetry run pre-commit run --all-files
```

The [Sphinx contribution guide](https://fastapi-logging-kit.readthedocs.io/en/latest/contributing.html)
has additional details. Keep `pyproject.toml`, `poetry.lock`, the tox matrix, CI, and documented runtime
support aligned when changing dependencies. Use `poetry add PACKAGE` for runtime
dependencies and `poetry add --group test PACKAGE` (or `quality`, `docs`, `build`)
for tooling. Run `poetry lock` after editing declarations and commit the lockfile.

## Pull requests

Add regression tests for behavior changes and update the relevant documentation
and `CHANGELOG.md`. Use Conventional Commits with one scope per commit, such as
`fix(logiboard): reject invalid permission results`. Describe the user-visible
change and the checks you ran. Open pull requests against `main`.

Use [GitHub issues](https://github.com/lazarus-org/fastapi-logging-kit/issues)
for reproducible bugs and feature proposals. Include Python and dependency
versions and a minimal example with sensitive log data removed.

## Releases (maintainers)

1. Update `[project].version`, `[tool.commitizen].version`, and the package's
   `__version__` together. Document the release in `CHANGELOG.md`.
2. Validate the release locally:

   ```sh
   poetry install --only main,build
   poetry build
   poetry run twine check dist/*
   poetry run python scripts/verify_distributions.py dist --tag v1.0.0
   ```

   Substitute the intended version for `v1.0.0` and use a clean `dist` directory;
   the verifier requires exactly one wheel and one source distribution.
3. After review, tag the release `v<version>`. The release workflow builds and
   verifies artifacts and calls the full CI workflow. A manual run on a branch
   validates the build without publishing.
4. Publishing is enabled only when the repository variable
   `PYPI_PUBLISH_ENABLED` is `true`. Configure a PyPI Trusted Publisher for this
   repository, `.github/workflows/release.yml`, and the `pypi` environment.
   Configure required reviewers on that GitHub environment if human approval
   is desired; an environment name alone does not enforce approval.


## Automatic Version Increment with Commitizen

Commitizen is already a development dependency. Use it to create Conventional
Commits interactively:

```sh
poetry run cz commit
```

Use one scope per commit. New features normally increment the minor version;
fixes and performance changes increment the patch version; breaking changes
increment the major version. Preview the computed release before changing files:

```sh
poetry run cz bump --dry-run
```

The project configuration synchronizes these version declarations:

```toml
[tool.commitizen]
name = "cz_conventional_commits"
version = "1.0.0"
version_files = [
    "pyproject.toml:^version =",
    "fastapi_logging_kit/__init__.py:__version__",
]
tag_format = "v$version"
```

The version in this example is the current baseline, not a value to copy over a
later release. `[project].version`, `[tool.commitizen].version`, and
`fastapi_logging_kit.__version__` must agree. Make releases from a clean, reviewed
`main` branch after the contribution has been merged.

### Generate the changelog and release together

```sh
poetry run cz bump --changelog --check-consistency
```

This selects the version from commit history, updates the configured version
files, updates `CHANGELOG.md`, creates the bump commit, and creates the `v<version>`
tag. Review the result before pushing. This command changes Git history locally;
it is a maintainer release step, not a requirement for every contribution.

### Keep a separate changelog commit

The original separate-changelog workflow is also available. First preview the
next version, then generate the incremental entry **before** creating its tag:

```sh
poetry run cz bump --dry-run
poetry run cz changelog --incremental --unreleased-version v1.1.0
git add CHANGELOG.md
git commit -m "docs(changelog): prepare release 1.1.0"
poetry run cz bump --check-consistency
```

Replace `v1.1.0` and `1.1.0` with the version selected by the preview. The
`--incremental` option retains earlier changelog entries. Preparing this commit
before the final bump ensures the release tag includes the changelog. Choose
this workflow or the combined `--changelog` workflow for a release, not both.
If Commitizen prompts about a missing initial version tag, confirm the repository
history and intended baseline before accepting.

## Export Dependencies

Dependency export remains available for production and development snapshots:

```sh
poetry self add poetry-plugin-export
poetry export -f requirements.txt --output requirements-export.txt --without-hashes
poetry export -f requirements.txt --with dev --output requirements-dev-export.txt --without-hashes
```

These optional exports are deployment snapshots, not project dependency sources.
The authoritative declarations are in `pyproject.toml`, and Poetry records the
resolved versions in `poetry.lock`. Dependabot updates those manager-native files;
do not introduce a second hand-maintained requirements manifest. If SQLAlchemy is needed in a deployment export, include
`--extras sqlalchemy`. Export is a development/maintenance step, not a reason to
change dependency files in every pull request.

## Publishing Guide

### Build and validate distributions

After the version bump, build from the release commit using a clean `dist`
directory. Archive any previous build artifacts separately first.

```sh
poetry build
poetry install --only main,build
poetry run twine check dist/*
poetry run python scripts/verify_distributions.py dist --tag v1.1.0
```

Replace `v1.1.0` with the actual release tag. The verifier checks version
consistency, runtime resources, CLI metadata, and wheel/source contents. Wheels
exclude internal tests; source distributions include tests, documentation,
project policies, and support scripts.

### Publish through GitHub Actions

After reviewing the release commit and tag, push the branch and that tag:

```sh
git push origin main
git push origin tag v1.1.0
```

The tag starts `.github/workflows/release.yml`. It builds distributions,
validates the tag, checks artifacts, and runs the reusable CI workflow. The
publish job waits for both build validation and CI to succeed.

To enable publication, maintainers configure:

1. A PyPI Trusted Publisher for the `fastapi-logging-kit` project, this GitHub
   repository, the workflow filename `release.yml`, and environment `pypi`.
2. The GitHub `pypi` environment. Add required reviewers there if releases should
   wait for human approval; naming an environment does not enforce approval.
3. Repository variable `PYPI_PUBLISH_ENABLED=true`.

With these settings, the workflow uses an OpenID Connect token to publish the
validated artifacts. A manual workflow run on a branch performs validation
without publishing. Do not also run a manual upload for the same release.

### TestPyPI and manual Poetry publishing

Manual publishing remains available for maintainers who explicitly choose that
route. Configure TestPyPI and provide its token through Poetry's secure keyring
or `POETRY_PYPI_TOKEN_TESTPYPI` in the publishing environment:

```sh
poetry config repositories.testpypi https://test.pypi.org/legacy/
poetry publish --repository testpypi --dry-run
poetry publish --repository testpypi
```

After checking the package in TestPyPI, publish the already validated build to
PyPI using the PyPI token supplied through a secure keyring or
`POETRY_PYPI_TOKEN_PYPI`:

```sh
poetry publish --dry-run
poetry publish
```

Do not commit tokens, put real credentials in documentation, or enable two
publishing routes for the same version. PyPI does not allow replacing an
existing release file. After publication, check the distribution version,
installation, CLI, and packaged resources in a fresh environment.

## Additional Resources

- [Commitizen bump commands](https://commitizen-tools.github.io/commitizen/commands/bump/)
- [Commitizen changelog commands](https://commitizen-tools.github.io/commitizen/commands/changelog/)
- [Poetry publishing](https://python-poetry.org/docs/cli/#publish)
- [Poetry export plugin](https://github.com/python-poetry/poetry-plugin-export)
- [PyPI Trusted Publishing](https://docs.pypi.org/trusted-publishers/)
