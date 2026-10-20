# Agent instructions

## Tests

Run the test suite with tox, e.g. `tox -e py313-dj52`. Pass test labels as
positional arguments to run a subset: `tox -e py313-dj52 -- testapp.test_forms`.

Tests live in `tests/testapp/` and use Django's `TestCase`.

## Conventions

- Pre-commit hooks (ruff check, ruff format, django-upgrade, …) run on commit;
  ruff enforces pep8-naming, so local variables must be lowercase.
- Add user-facing changes to `CHANGELOG.rst` under "Next version". Separate
  version sections with two blank lines.
