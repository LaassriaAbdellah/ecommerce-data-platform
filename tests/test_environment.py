"""Check the runtime used for local development."""
import sys


def test_python_version():
    assert sys.version_info >= (3, 11), "Python 3.11 or newer is required"


def test_virtual_environment():
    assert sys.prefix != sys.base_prefix, "Run tests with the project .venv"
