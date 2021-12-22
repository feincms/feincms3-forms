==============
feincms3-forms
==============

.. image:: https://github.com/matthiask/feincms3-forms/actions/workflows/tests.yml/badge.svg
    :target: https://github.com/matthiask/feincms3-forms/
    :alt: CI Status


No documentation yet, sorry. You have to look at the testsuite.

Design decisions
================

This is a list of things which should be explained but are not at the moment.

- Form fields have to inherit ``FormFieldBase``. ``FormFieldBase`` only has a
  ``name`` field. This field can be checked for clashes etc. The base class is
  used instead of duck typing in various places where the code may encounter
  not only form field plugins but also other django-content-editor plugins. The
  latter are useful e.g. to add blocks of text or other content between form
  fields.
- The ``FormField`` offers a basic set of attributes for standard fields such
  as a label, a help text and whether the field should be required or not.
- The ``SimpleFieldBase`` should be instantiated in your project and can be
  used to cheaply generate standard form field plugin proxies for HTML5 input
  fields. (Sorry for the jargon.) Those proxies are standard Django model
  proxies.
