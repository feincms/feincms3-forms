==========
Change log
==========

Next version
~~~~~~~~~~~~

- Restored the lower Django bound to 3.2.
- Added Django 5.2, Python 3.13.
- Added more docs and many many recipes.
- Added a ``strip_name_prefix`` boolean argument to ``get_form_fields`` which
  simplifies referencing individual form fields in templates.


0.5 (2024-08-20)
~~~~~~~~~~~~~~~~

- Removed testing for Django older than 4.2.
- Allowed setting a maximal length for URL and email fields.


0.4 (2023-07-27)
~~~~~~~~~~~~~~~~

- Increased the test coverage.
- Defined default content editor button icons for simple fields.
- Switched to hatchling and ruff.
- Added testing using Django 4.2, 5.0, 5.1 and Python 3.11, 3.12.


`0.3`_ (2022-11-22)
~~~~~~~~~~~~~~~~~~~

.. _0.3: https://github.com/matthiask/feincms3-forms/compare/0.2...0.3

- Added multiple select and multiple checkboxes field types to the simple field
  base.
- Changed the ``SELECT`` simple field type to use the placeholder field to
  replace the default empty choices string if set.
- Renamed ``SimpleFieldBase.get_fields`` to ``SimpleFieldBase.get_field`` to
  enable better code reuse without ``super()``.


`0.2`_ (2022-11-11)
~~~~~~~~~~~~~~~~~~~

.. _0.2: https://github.com/matthiask/feincms3-forms/compare/0.1...0.2

- Changed ``ConfiguredForm.get_formfields_union`` to allow fetching arbitrary
  attributes from plugins, completely changed the return value to a list of
  ``(name, {...attributes...})`` tuples, made validation utilities work with
  this new data structure.


`0.1`_ (2022-11-10)
~~~~~~~~~~~~~~~~~~~

- Time to leave the zero.zero.whatever versions behind!


.. _0.1: https://github.com/matthiask/feincms3-forms/commit/93cba055a85
