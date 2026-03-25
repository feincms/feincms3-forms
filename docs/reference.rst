Reference
=========


Models
------


FormFieldBase
~~~~~~~~~~~~~

``FormFieldBase`` is the base class all form field plugins must inherit from. It
has a single ``name`` field used to identify the field in submitted data and for
clash detection. The base class is used instead of duck typing in places where
the code encounters a mix of form field plugins and other
django-content-editor plugins (e.g. rich text blocks between fields).

``FormFieldBase`` defines the form field plugin API:

- ``get_fields(**kwargs)``: Return a dictionary of Django form fields.
- ``get_initial()``: Return a dictionary of initial values for those fields.
- ``get_cleaners()``: Return a list of callables which receive the form
  instance, return cleaned data, and may raise ``ValidationError``.
- ``get_loaders()``: Return a list of loader callables (see `Loaders`_ below).


FormField
~~~~~~~~~

``FormField`` extends ``FormFieldBase`` with a standard set of attributes for
typical form fields: ``label``, ``help_text``, and ``is_required``. You do not
have to use this model — it exists to provide useful defaults for common cases.


SimpleFieldBase
~~~~~~~~~~~~~~~

``SimpleFieldBase`` covers many standard field types (text, email, URL, date,
integer, textarea, checkbox, select, radio, and multi-select) with a single
database table, using Django's proxy model mechanism.

Instantiate it in your project and create proxy models for each field type you
need:

.. code-block:: python

    class SimpleField(forms_models.SimpleFieldBase, ConfiguredFormPlugin):
        pass

    Text = SimpleField.proxy(SimpleField.Type.TEXT)
    Email = SimpleField.proxy(SimpleField.Type.EMAIL)
    Select = SimpleField.proxy(SimpleField.Type.SELECT)
    # etc.

``SimpleFieldBase`` has a corresponding ``SimpleFieldInline`` in
``feincms3_forms.admin`` which shows and hides admin fields depending on the
field type — for example, it hides the placeholder field for checkboxes since
browsers do not support them.


ConfiguredForm and FormType
~~~~~~~~~~~~~~~~~~~~~~~~~~~

``ConfiguredForm`` is the top-level model that ties a form together. Subclass
it in your project and define ``FORMS`` as a list of ``FormType`` instances,
one per form variant your project supports.

``FormType`` accepts:

- ``key``: A unique string identifier.
- ``label``: Human-readable name shown in the admin.
- ``regions``: A list of ``Region`` objects, or a callable that takes the
  ``ConfiguredForm`` instance and returns a list of regions.
- ``form_class`` *(optional)*: Dotted path to a base form class for the
  dynamically created form.
- ``validate`` *(optional)*: Dotted path to a validation function called by
  ``ConfiguredFormAdmin``.
- ``process`` *(optional)*: Dotted path to the function called after a valid
  submission. feincms3-forms never calls this directly, but it's a useful
  convention.


Renderer
--------

The renderer is responsible for creating and instantiating the Django form
class from a list of content editor plugins.

``create_form(plugins, form_class=None, form_kwargs=None)``
    Creates and instantiates a form from a list of plugins. ``form_class``
    defaults to a plain ``forms.Form``. ``form_kwargs`` are passed to the form
    constructor.

``short_prefix(obj, suffix)``
    Returns a short, stable form prefix string based on the object's primary
    key. Useful when multiple forms may appear on the same page.

The created form has a ``get_form_fields(plugin, strip_name_prefix=False)``
method that returns a dictionary of bound form fields for the given plugin.
Pass ``strip_name_prefix=True`` to strip the plugin's ``name`` prefix from
the dictionary keys, which makes it easier to reference fields by simple names
in templates (see :ref:`strip-name-prefix`).


Validation
----------

The ``feincms3_forms.validation`` module provides validators for checking
that a configured form meets your application's requirements. These are called
from your ``validate`` function, which ``ConfiguredFormAdmin`` invokes
automatically.

``validate_uniqueness(fields)``
    Checks for duplicate field names. Returns warnings for any duplicates.

``validate_required_fields(fields, required)``
    Checks that all field names in ``required`` are present. Returns errors for
    missing fields.

``validate_fields(fields, schema)``
    Validates fields against a schema dict mapping field names to expected
    attributes (``type``, ``is_required``, etc.). Returns warnings for missing
    fields and errors for attribute mismatches.

Example validation function:

.. code-block:: python

    from feincms3_forms.validation import (
        validate_fields,
        validate_required_fields,
        validate_uniqueness,
    )

    def validate_contact_form(configured_form):
        fields = configured_form.get_formfields_union(
            plugins=renderer.plugins(), attributes=["type", "is_required"]
        )
        return [
            *validate_uniqueness(fields),
            *validate_required_fields(fields, {"email"}),
            *validate_fields(
                fields,
                {
                    "email": {"type": "email", "is_required": True},
                },
            ),
        ]

Reference the function in your ``FormType``:

.. code-block:: python

    forms_models.FormType(
        key="contact",
        label="contact form",
        regions=[Region(key="form", title="form")],
        validate="app.forms.forms.validate_contact_form",
        process="app.forms.forms.process_contact_form",
    )


Loaders
-------

Loaders convert serialized form submission data (stored as a JSON dict) back
into a human-readable format for display and export. Each form field plugin
should implement ``get_loaders()`` returning a list of loader callables. Each
loader takes the submission data dict and returns a dict::

    {"name": "field_name", "label": "Field Label", "value": "submitted value"}

Simple loader:

.. code-block:: python

    from functools import partial
    from feincms3_forms.models import simple_loader

    class MyField(FormFieldBase, ConfiguredFormPlugin):
        label = models.CharField(max_length=200)

        def get_loaders(self):
            return [partial(simple_loader, label=self.label, name=self.name)]

Compound fields (those that generate multiple form fields) return multiple
loaders, one per generated field:

.. code-block:: python

    def get_loaders(self):
        return [
            partial(simple_loader, label=self.label_from, name=f"{self.name}_from"),
            partial(simple_loader, label=self.label_until, name=f"{self.name}_until"),
        ]


Reporting
---------

The ``feincms3_forms.reporting`` module provides helpers for working with
submission data.

``get_loaders(plugins)``
    Collects all loaders from a list of plugin instances and returns a flat
    list of loader callables:

    .. code-block:: python

        from content_editor.contents import contents_for_item
        from feincms3_forms.reporting import get_loaders

        contents = contents_for_item(configured_form, plugins=renderer.plugins())
        loaders = get_loaders(contents)
        for loader in loaders:
            row = loader(submitted_data)
            print(f"{row['label']}: {row['value']}")

``simple_report(contents, data)``
    Generates an HTML summary of submitted data suitable for display in the
    Django admin:

    .. code-block:: python

        from django.contrib.admin import display
        from feincms3_forms.reporting import simple_report

        @display(description="Submitted Data")
        def pretty_data(self, obj):
            return simple_report(
                contents=contents_for_item(
                    obj.configured_form, plugins=renderer.plugins()
                ),
                data=obj.data,
            )

``value_default(row, default="Ø")``
    Returns ``default`` when the field value in ``row`` is empty:

    .. code-block:: python

        values = [value_default(loader(data)) for loader in loaders]
