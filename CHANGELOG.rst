==========
Change log
==========

`Next version`_
~~~~~~~~~~~~~~~

.. _Next version: https://github.com/matthiask/feincms3-forms/compare/0.2...main

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
