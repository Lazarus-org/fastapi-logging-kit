## Code of Conduct for Contributing to fastapi_logging_kit

we’re thrilled that you want to contribute to `fastapi_logging_kit`! to ensure a positive and protective environment for everyone involved, please adhere to the following guidelines.

## Contribution Workflow

1. **Fork and Clone**: Start by forking the `fastapi_logging_kit` repository on Github and cloning it to your local machine:
    ```bash
    git clone https://github.com/lazarus-org/fastapi-logging-kit.git
    cd fastapi-logging-kit
    ```

2. **Create a Branch**: Create a new branch for your feature or bugfix:
    ```bash
    git checkout -b feature/your-feature-name
    ```

3. **Install Dependencies**: Use Poetry to install the project’s dependencies. if poetry isn’t installed, refer to the [Poetry installation guide](https://python-poetry.org/docs/#installation)
    ```bash
    poetry install --extras sqlalchemy
    ```

4. **Write Code and Tests**: Make your changes and write tests for your new code. Ensure that all tests pass:
   ```bash
    poetry run pytest
    ```
5. **Run Code Quality Checks**: Ensure code quality with Pylint:
    ```bash
    poetry run pylint fastapi_logging_kit
    ```

6. **Commit Your Changes**: Use Commitizen to commit your changes according to the Conventional Commits specification:
    ```bash
    poetry run cz commit
    ```

7. **Push and Create a PR**: Push your changes to your fork on GitHub and open a pull request:
    ```bash
    git push origin feature/your-feature-name
    ```

8. **Bump Version**: Use Commitizen to automatically update the version number based on commit messages.

   First, confirm the current version in the Commitizen configuration (`pyproject.toml`) under `[tool.commitizen]`. For instance:
   ```text
   [tool.commitizen]
   version = "1.0.0"
   ```
   Preview the automatic increment first; the final bump is performed in step 10 after preparing the changelog:
    ```bash
    poetry run cz bump --dry-run
    ```
   Commitizen analyzes Conventional Commits to select a major, minor, or patch increment. The configured version_files synchronize the distribution version and package __version__. The dry run does not create a release commit or tag.

9. **Generate Changelog**: Generate the incremental changelog for the planned release before creating its tag. Replace v1.1.0 with the version reported by the dry run:
    ```bash
    poetry run cz changelog --incremental --unreleased-version v1.1.0
    ```
    the `--incremental` option limits changelog updates to only the new version tag, leaving previous entries unchanged. After generating the changelog, add it to the staging area and commit it manually:

    ```bash
    git add CHANGELOG.md
    git commit -m "docs: update changelog for new version"
    ```
   This separate commit avoids including the changelog entry in the release notes, keeping them focused on code changes.

10. **Push Code and Tag**: Push the updated code and new version tag to GitHub. After review and merge, run the final automatic bump from a clean main branch:

   ```shell
   poetry run cz bump --check-consistency
   ```

   This updates the configured version files and creates the release commit and v<version> tag. Alternatively, use `poetry run cz bump --changelog --check-consistency` to include the changelog in the bump commit instead of using the separate changelog commit in step 9. Do not run both bump variants for the same release.

   ```shell
   git push origin main
   git push origin tag v1.1.0
   ```
   The first command pushes your code changes, and the second command pushes the new version tag created by Commitizen. This ensures that the tag is available on GitHub, which is useful for creating releases and tracking versioned changes.

11. **Export Dependencies**: Export the project dependencies for development and production:
    ```bash
    poetry self add poetry-plugin-export

    poetry export -f requirements.txt --output requirements-export.txt --without-hashes
    poetry export -f requirements.txt --with dev --output requirements-dev-export.txt --without-hashes
    ```

Exported files are optional deployment snapshots. Manage runtime and development dependency groups directly in `pyproject.toml` with Poetry, and commit `poetry.lock` after dependency changes. The project does not maintain parallel requirements manifests.

For artifact validation, PyPI Trusted Publishing, TestPyPI, and manual publishing, see the detailed [publishing guide](CONTRIBUTING.md#publishing-guide).

## Commitizen Message Rule

Commitizen follows the Conventional Commits specification. Your commit message should be structured as follows:

```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

## Example of Commit Messages

### 1. Initialization of Core
```
feat(core): initialize the core module

- Set up the core structure
- Added initial configurations and settings
- Created basic utility functions
```

### 2. Release with Build and Tag Version
```
chore(release): build and tag version 1.0.0

- Built the project for production
- Created a new tag for version 1.0.0
- Updated changelog with release notes
```

### 3. Adding a New Feature
```
feat(auth): add user authentication

- Implemented user login and registration
- Added JWT token generation and validation
- Created middleware for protected routes
```

### 4. Fixing a Bug
```
fix(api): resolve issue with data fetching

- Fixed bug causing incorrect data responses
- Improved error handling in API calls
- Added tests for the fixed bug
```

### 5. Update Documentation (Sphinx)
```
docs(sphinx): update API documentation

- Updated the Sphinx documentation for API changes
- Added examples for new endpoints
- Fixed typos and formatting issues
```

### 6. Update Dependencies
```
chore(deps): update project dependencies

- Updated all outdated Python dependencies
- Resolved compatibility issues with new package versions
- Ran tests to ensure no breaking changes
```

### 7. Update Version for Build and Publish
```
chore(version): update version to 1.1.0 for build and publish

- Incremented version number to 1.1.0
- Updated pyproject.toml and fastapi_logging_kit/__init__.py with the new version
- Prepared for publishing the new build
```

### 8. Adding Unit Tests
```
test(auth): add unit tests for authentication module

- Created tests for login functionality
- Added tests for registration validation
- Ensured 100% coverage for auth module
```

### 9. Refactoring Codebase
```
refactor(core): improve code structure and readability

- Refactored core module to enhance readability
- Extracted utility functions into separate files
- Updated documentation to reflect code changes
```

### 10. Improving Performance
```
perf(parser): enhance parsing speed

- Optimized parsing algorithm for better performance
- Reduced the time complexity of the parsing function
- Added benchmarks to track performance improvements
```

Thank you for contributing to `fastapi_logging_kit`! We look forward to your contributions.


Everyone participating in this project is expected to help maintain a welcoming,
respectful environment, regardless of background, experience, identity, or ability.

## Expected behavior

- Be considerate in issues, pull requests, reviews, and discussions.
- Give constructive feedback about the work and accept corrections in good faith.
- Respect privacy; remove credentials and personal data from shared logs and examples.
- Credit contributions and focus disagreements on technical decisions.

## Unacceptable behavior

Harassment, discrimination, threats, personal attacks, unwanted sexual attention,
and publishing private information without consent are unacceptable. Repeated
disruption or retaliation against someone reporting a concern is also unacceptable.

## Reporting and enforcement

Report conduct concerns privately to [Aryan Niknezhad](mailto:aryan513966@gmail.com)
or [Mehrshad Mirshekary](mailto:mehrshad_mirshekary@email.com). Include the relevant
context and links when available. Maintainers will review reports with discretion,
respect the privacy of those involved, and may edit or remove content, restrict
participation, or exclude participants when necessary.

This policy applies to project spaces and to people representing the project in
public. Development and release instructions are in [CONTRIBUTING.md](CONTRIBUTING.md).
