==============
feincms3-forms
==============

.. image:: https://github.com/matthiask/feincms3-forms/actions/workflows/tests.yml/badge.svg
    :target: https://github.com/matthiask/feincms3-forms/
    :alt: CI Status

This is an extremely flexible forms builder for the Django admin interface.

If you only want to integrate short and simple forms (e.g. a contact form)
you're probably better off using `form_designer
<https://github.com/feincms/form_designer>`__. The feincms3 documentation
contains a `guide showing how to integrate it
<https://feincms3.readthedocs.io/en/latest/guides/apps-form-builder.html>`__.

If you need more flexibility, multi page forms, forms with other content
between fields, a relatively straightforward way to define you own (compound)
fields etc. etc. then feincms3-forms may be for you.


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
