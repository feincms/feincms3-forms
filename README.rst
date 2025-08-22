==============
feincms3-forms
==============

.. image:: https://github.com/matthiask/feincms3-forms/actions/workflows/tests.yml/badge.svg
    :target: https://github.com/matthiask/feincms3-forms/
    :alt: CI Status

This is an extremely flexible forms builder for the Django admin interface. It
allows using `django-content-editor
<https://django-content-editor.readthedocs.io/>`__ for your form which enables:

- Build your own form in the CMS and not have to ask programmers to change
  anything.
- Reorder, add and remove pre-existing fields.
- Add content (text, images, anything) between form fields.
- Use regions to add additional structure to a form, e.g. to build configurable
  multi-step forms (wizards).
- Add your own form field plugins with all the flexibility and configurability
  you desire.

If you only want to integrate short and simple forms (e.g. a contact form)
you're probably better off using `form_designer
<https://github.com/feincms/form_designer>`__. The feincms3 documentation
contains a `guide showing how to integrate it
<https://feincms3.readthedocs.io/en/latest/guides/apps-form-builder.html>`__.


High level overview
===================

The documentation is very sparse, sorry for that.


Models
~~~~~~


FormFieldBase
-------------

Form fields have to inherit ``FormFieldBase``. ``FormFieldBase`` only has a
``name`` field. This field can be checked for clashes etc. The base class is
used instead of duck typing in various places where the code may encounter not
only form field plugins but also other django-content-editor plugins. The
latter are useful e.g. to add blocks of text or other content between form
fields.

The ``FormFieldBase`` model defines the basic API of form fields:

- ``get_fields()``: Return a dictionary of form fields.
- ``get_initial()``: Return initial values of said fields.
- ``get_cleaners()``: Return a list of callables which receive the form
  instance, return the cleaned data and may raise ``ValidationError``
  exceptions.
- ``get_loaders()``: Return a list of loaders. The purpose of loaders is to
  load form submissions, e.g. for reporting purposes. Loaders are callables
  which receive the serialized form data and return a dictionary of the
  following shape: ``{"name": ..., "label": ..., "value": ...}``.


FormField
---------

The ``FormField`` offers a basic set of attributes for standard fields such as
a label, a help text and whether the field should be required or not. You do
not have to use this model if you want to define your own. It's purpose is just
to offer a few good defaults.


SimpleFieldBase
---------------

The ``SimpleFieldBase`` should be instantiated in your project and can be used
to cheaply add support for many basic field types such as text fields, email
fields, checkboxes, choice fields and more with a single backing database table
and model.

The ``SimpleFieldBase`` has a corresponding ``SimpleFieldInline`` in the
``feincms3_forms.admin`` module which shows and hides fields depending on the
field type. For example, it makes no sense to define placeholders for
checkboxes (browsers do not support them) therefore the field is omitted in the
CMS.


Renderer
~~~~~~~~

The renderer functions are responsible for creating and instantiating the form
class. Form class creation and instantiation happens at once.


Validation
~~~~~~~~~~

The validation module offers utilities to validate a form when it is defined in
the CMS. For example, the backend code may require that an email field always
exists and always has a certain predefined name (for example ``email`` 😏).
These rules are not enforced at the moment but the user is always notified and
can therefore choose to heed them. Or bad things may happen depending on the
code you write.

The ``feincms3_forms.validation`` module provides the following validators:

- ``validate_uniqueness(fields)``: Checks for duplicate field names and returns
  warnings if any fields appear more than once.
- ``validate_required_fields(fields, required)``: Ensures that all specified
  required field names are present in the form, returning errors for any missing
  required fields.
- ``validate_fields(fields, schema)``: Validates that fields match a given schema,
  checking attributes like ``type`` and ``is_required``. Returns warnings for
  missing expected fields and errors for fields that don't match the expected
  attributes.

These validators can be used in your form type's ``validate`` function. For
example:

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

Then reference this validation function in your ``ConfiguredForm`` model:

.. code-block:: python

    class ConfiguredForm(forms_models.ConfiguredForm):
        FORMS = [
            forms_models.FormType(
                key="contact",
                label="contact form",
                regions=[Region(key="form", title="form")],
                validate="app.forms.forms.validate_contact_form",
                process="app.forms.forms.process_contact_form",
            ),
        ]


Reporting
~~~~~~~~~

The reporting functions are mostly useful if you want to do something with
submitted data.


Installation and usage
======================

Create a module containing the models for the form builder (``app.forms.models``):

.. code-block:: python

    from content_editor.models import Region, create_plugin_base
    from django.db import models
    from feincms3 import plugins
    from feincms3_forms import models as forms_models

    class ConfiguredForm(forms_models.ConfiguredForm):
        FORMS = [
            forms_models.FormType(
                key="contact",
                label="contact form",
                regions=[Region(key="form", title="form")],

                # Base class for the dynamically created form:
                # form_class="...",

                # Validation hook for configured form (the bundled ModelAdmin
                # class calls this):
                # validate="...",

                # Processing function which you can call after submission
                # (feincms3-forms never calls this function itself, but it
                # may be a nice convention):
                process="app.forms.forms.process_contact_form",
            ),
        ]

    ConfiguredFormPlugin = create_plugin_base(ConfiguredForm)

    class SimpleField(forms_models.SimpleFieldBase, ConfiguredFormPlugin):
        pass

    Text = SimpleField.proxy(SimpleField.Type.TEXT)
    Email = SimpleField.proxy(SimpleField.Type.EMAIL)
    URL = SimpleField.proxy(SimpleField.Type.URL)
    Date = SimpleField.proxy(SimpleField.Type.DATE)
    Integer = SimpleField.proxy(SimpleField.Type.INTEGER)
    Textarea = SimpleField.proxy(SimpleField.Type.TEXTAREA)
    Checkbox = SimpleField.proxy(SimpleField.Type.CHECKBOX)
    Select = SimpleField.proxy(SimpleField.Type.SELECT)
    Radio = SimpleField.proxy(SimpleField.Type.RADIO)
    SelectMultiple = SimpleField.proxy(SimpleField.Type.SELECT_MULTIPLE)
    CheckboxSelectMultiple = SimpleField.proxy(SimpleField.Type.CHECKBOX_SELECT_MULTIPLE)

    class RichText(plugins.richtext.RichText, ConfiguredFormPlugin):
        pass

Add the processing function referenced above (``app.forms.forms``):

.. code-block:: python

    from django.core.mail import mail_managers
    from django.http import HttpResponse

    def process_contact_form(request, form, *, configured_form):
        mail_managers("Contact form", repr(form.cleaned_data))
        return HttpResponseRedirect(".")

Add the renderer and the view (``app.forms.views``):

.. code-block:: python

    from content_editor.contents import contents_for_item
    from django.shortcuts import render
    from feincms3.renderer import RegionRenderer, render_in_context, template_renderer
    from feincms3_forms.renderer import create_form, short_prefix
    from app.forms import models

    renderer = RegionRenderer()
    renderer.register(models.RichText, template_renderer("plugins/richtext.html"))
    renderer.register(
        models.SimpleField,
        lambda plugin, context: render_in_context(
            context,
            "forms/simple-field.html",
            {"plugin": plugin, "fields": context["form"].get_form_fields(plugin)},
        ),
    )

    def form(request):
        context = {}
        cf = models.ConfiguredForm.objects.first()

        contents = contents_for_item(cf, plugins=renderer.plugins())

        # Add a prefix in case more than one form exists on the same page:
        form_kwargs = {"prefix": short_prefix(cf, "form")}

        if request.method == "POST":
            form_kwargs |= {"data": request.POST, "files": request.FILES}

        form = create_form(
            contents["form"],
            form_class=cf.type.form_class,
            form_kwargs=form_kwargs,
        )

        if form.is_valid():
            return cf.type.process(request, form, configured_form=cf)

        context["form"] = form
        context["form_other_fields"] = form.get_form_fields(None)
        context["form_regions"] = renderer.regions_from_contents(contents)

        return render(request, "forms/form.html", context)

The ``forms/simple-field.html`` template referenced above might look as
follows:

.. code-block:: html+django

    {% for field in fields.values %}{{ field }}{% endfor %}

An example ``forms/form.html``:

.. code-block:: html+django

    {% extends "base.html" %}

    {% load feincms3 i18n %}

    {% block content %}
    <div class="content">
      <form class="form" method="post">
        {% csrf_token %}
        {{ form.errors }}
        {% render_region form_regions 'form' %}
        {% for field in form_other_fields.values %}{{ field }}{% endfor %}
        <button type="submit">Submit</button>
      </form>
    </div>
    {% endblock content %}

Finally, the form would have to be added to the admin site (``app.forms.admin``):

.. code-block:: python

    from content_editor.admin import ContentEditorInline
    from django.contrib import admin
    from feincms3 import plugins
    from feincms3_forms.admin import ConfiguredFormAdmin, SimpleFieldInline

    from app.forms import models


    @admin.register(models.ConfiguredForm)
    class ConfiguredFormAdmin(ConfiguredFormAdmin):
        inlines = [
            plugins.richtext.RichTextInline.create(model=models.RichText),
            SimpleFieldInline.create(
                model=models.Text,
                button='<i class="material-icons">short_text</i>',
            ),
            SimpleFieldInline.create(
                model=models.Email,
                button='<i class="material-icons">alternate_email</i>',
            ),
            SimpleFieldInline.create(
                model=models.URL,
                button='<i class="material-icons">link</i>',
            ),
            SimpleFieldInline.create(
                model=models.Date,
                button='<i class="material-icons">event</i>',
            ),
            SimpleFieldInline.create(
                model=models.Integer,
                button='<i class="material-icons">looks_one</i>',
            ),
            SimpleFieldInline.create(
                model=models.Textarea,
                button='<i class="material-icons">notes</i>',
            ),
            SimpleFieldInline.create(
                model=models.Checkbox,
                button='<i class="material-icons">check_box</i>',
            ),
            SimpleFieldInline.create(
                model=models.Select,
                button='<i class="material-icons">arrow_drop_down_circle</i>',
            ),
            SimpleFieldInline.create(
                model=models.Radio,
                button='<i class="material-icons">radio_button_checked</i>',
            ),
        ]

And last but not least, create and apply migrations. That should be basically
it. We haven't touched validating the configured form, reporting utilities or
creating your own (compound) field types yet, for now you have to check the
testsuite.
