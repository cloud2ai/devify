"""
Nox configuration for Devify project

Unified development command entry point - simplified version
using existing environment
"""

import nox

# Disable virtual environment, use current environment
nox.options.sessions = ["eml_tests", "tests", "format"]


@nox.session(venv_backend="none")
def eml_tests(session):
    """
    Run EML email parsing tests
    """
    session.log("🧪 Running EML email parsing tests")

    # Use existing environment to run tests
    session.run(
        "python", "-m", "pytest",
        "devify/threadline/tests/functional/test_eml_parsing.py",
        "-v", "-s",
        env={"DJANGO_SETTINGS_MODULE": "devify.core.settings"}
    )


@nox.session(venv_backend="none")
def tests(session):
    """
    Run all tests
    """
    session.log("🧪 Running all tests")

    session.run(
        "python", "-m", "pytest",
        "devify/threadline/tests/",
        "-v",
        env={"DJANGO_SETTINGS_MODULE": "devify.core.settings"}
    )


@nox.session(venv_backend="none")
def unit_tests(session):
    """
    Run unit tests
    """
    session.log("🧪 Running unit tests")

    session.run(
        "python", "-m", "pytest",
        "devify/threadline/tests/unit/",
        "-v",
        env={"DJANGO_SETTINGS_MODULE": "devify.core.settings"}
    )


def _run_threadline_e2e_tests(session):
    session.run(
        "python", "-m", "pytest",
        "devify/threadline/tests/e2e/",
        "-v",
        env={"DJANGO_SETTINGS_MODULE": "devify.core.settings"}
    )


@nox.session(venv_backend="none")
def e2e_tests(session):
    """
    Run end-to-end tests
    """
    session.log("🧪 Running end-to-end tests")
    _run_threadline_e2e_tests(session)


@nox.session(venv_backend="none")
def api_tests(session):
    """
    Backward-compatible alias for end-to-end tests.
    """
    session.log("🧪 Running end-to-end tests (legacy api_tests alias)")
    _run_threadline_e2e_tests(session)


@nox.session(venv_backend="none")
def functional_tests(session):
    """
    Run functional tests
    """
    session.log("🧪 Running functional tests")

    session.run(
        "python", "-m", "pytest",
        "devify/threadline/tests/functional/",
        "-v",
        env={"DJANGO_SETTINGS_MODULE": "devify.core.settings"}
    )


@nox.session(venv_backend="none")
def coverage(session):
    """
    Generate test coverage report
    """
    session.log("📊 Generating test coverage report")

    session.run(
        "python", "-m", "pytest",
        "devify/threadline/tests/",
        "--cov=devify.threadline",
        "--cov-report=html",
        "--cov-report=term-missing",
        env={"DJANGO_SETTINGS_MODULE": "devify.core.settings"}
    )


@nox.session(venv_backend="none")
def format(session):
    """
    Auto format code
    """
    session.log("🔧 Auto formatting code")

    try:
        session.run("black", "devify/")
        session.run("isort", "devify/")
        session.log("✅ Code formatting completed")
    except Exception as e:
        session.log(f"⚠️  Formatting failed: {e}")
        session.log("Please ensure installed: pip install black isort")


@nox.session(venv_backend="none")
def lint(session):
    """
    Code quality check
    """
    session.log("🔍 Running code quality check")

    try:
        session.run("black", "devify/", "--check", "--diff")
        session.run("isort", "devify/", "--check-only", "--diff")
        session.log("✅ Code quality check passed")
    except Exception as e:
        session.log(f"⚠️  Code quality check failed: {e}")


@nox.session(venv_backend="none")
def django_check(session):
    """
    Django system check
    """
    session.log("🔍 Running Django system check")

    session.run(
        "python", "devify/manage.py", "check",
        env={"DJANGO_SETTINGS_MODULE": "devify.core.settings"}
    )


@nox.session(venv_backend="none")
def runserver(session):
    """
    Start development server
    """
    port = session.posargs[0] if session.posargs else "8000"
    session.log(f"🚀 Starting development server (port: {port})")

    session.run(
        "python", "devify/manage.py", "runserver", f"0.0.0.0:{port}",
        env={"DJANGO_SETTINGS_MODULE": "devify.core.settings"}
    )


# Convenient aliases
@nox.session(venv_backend="none")
def test(session):
    """Alias for tests"""
    tests(session)


@nox.session(venv_backend="none")
def cov(session):
    """Alias for coverage"""
    coverage(session)
