Development
===========

Running tests
-------------

Tests are run with tox::

    tox

Code style
----------

This project uses pre-commit hooks for code style. Set them up with::

    uv tool install pre-commit
    pre-commit install

Pre-commit runs Ruff for Python linting and formatting, and a few other hooks.
