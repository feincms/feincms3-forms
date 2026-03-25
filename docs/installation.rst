Installation and setup
======================

Install the package::

    pip install feincms3-forms

feincms3-forms does not require an entry in ``INSTALLED_APPS``.


Basic setup
-----------

The following steps walk through a complete minimal setup. More advanced
patterns are covered in :doc:`recipes`.


Models
~~~~~~

Create a module for your form builder models (e.g. ``app/forms/models.py``):

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

                # Optional: base class for the dynamically created form:
                # form_class="...",

                # Optional: validation hook called by the bundled ModelAdmin:
                # validate="...",

                # Optional: processing function called after a valid submission:
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


Processing function
~~~~~~~~~~~~~~~~~~~

Add the processing function referenced above (e.g. ``app/forms/forms.py``):

.. code-block:: python

    from django.core.mail import mail_managers
    from django.http import HttpResponseRedirect

    def process_contact_form(request, form, *, configured_form):
        mail_managers("Contact form", repr(form.cleaned_data))
        return HttpResponseRedirect(".")


Renderer and view
~~~~~~~~~~~~~~~~~

Add the renderer and view (e.g. ``app/forms/views.py``):

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


Templates
~~~~~~~~~

``forms/simple-field.html``:

.. code-block:: html+django

    {% for field in fields.values %}{{ field }}{% endfor %}

``forms/form.html``:

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


Admin
~~~~~

Register the form in the admin (e.g. ``app/forms/admin.py``):

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

Create and apply migrations::

    python manage.py makemigrations
    python manage.py migrate
