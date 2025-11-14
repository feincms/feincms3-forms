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


Loaders
~~~~~~~

Loaders are responsible for extracting and formatting submitted form data for
display and export purposes. They convert the serialized form data (typically
stored as JSON) back into a human-readable format.

Each form field plugin that inherits from ``FormFieldBase`` should implement a
``get_loaders()`` method that returns a list of loader callables. Each loader
receives the serialized form data dictionary and returns a dictionary with the
following structure:

.. code-block:: python

    {
        "name": "field_name",      # The field name/key in the data
        "label": "Field Label",    # Human-readable label
        "value": "field value",    # The actual value
    }

Example loader implementation for a simple field:

.. code-block:: python

    from functools import partial
    from feincms3_forms.models import simple_loader

    class MyField(FormFieldBase, ConfiguredFormPlugin):
        label = models.CharField(max_length=200)

        def get_loaders(self):
            return [
                partial(simple_loader, label=self.label, name=self.name)
            ]

For compound fields that generate multiple form fields, return multiple loaders:

.. code-block:: python

    class Duration(FormFieldBase, ConfiguredFormPlugin):
        label_from = models.CharField(max_length=1000)
        label_until = models.CharField(max_length=1000)

        def get_loaders(self):
            return [
                partial(
                    simple_loader,
                    label=self.label_from,
                    name=f"{self.name}_from",
                ),
                partial(
                    simple_loader,
                    label=self.label_until,
                    name=f"{self.name}_until",
                ),
            ]

Custom loaders can perform additional processing on the data:

.. code-block:: python

    class Upload(FormField, ConfiguredFormPlugin):
        def get_loaders(self):
            def loader(data):
                row = {"label": self.label, "name": self.name}
                if value := data.get(self.name):
                    # Convert file path to full URL
                    row["value"] = f"{settings.DOMAIN}{storage.url(value)}"
                else:
                    row["value"] = ""
                return row

            return [loader]


Reporting
~~~~~~~~~

The reporting module provides utilities for working with submitted form data.
The main functions are:

**get_loaders(plugins)**

Collects all loaders from form field plugins. Takes a list of plugin instances
and returns a flat list of all loader callables.

.. code-block:: python

    from content_editor.contents import contents_for_item
    from feincms3_forms.reporting import get_loaders

    contents = contents_for_item(configured_form, plugins=renderer.plugins())
    loaders = get_loaders(contents)

    # Apply loaders to extract data
    for loader in loaders:
        row = loader(submitted_data)
        print(f"{row['label']}: {row['value']}")

**simple_report(contents, data)**

Generates an HTML representation of submitted form data for display in the
Django admin interface. Returns a safe HTML string with formatted field labels
and values.

.. code-block:: python

    from django.contrib.admin import display
    from feincms3_forms.reporting import simple_report

    @display(description="Submitted Data")
    def pretty_data(self, obj):
        return simple_report(
            contents=contents_for_item(obj.configured_form, plugins=renderer.plugins()),
            data=obj.data,
        )

**value_default(row, default="Ø")**

Helper function that returns a default value if the field value is empty.

.. code-block:: python

    from feincms3_forms.reporting import value_default

    values = [value_default(loader(data)) for loader in loaders]


Exporting submitted data
~~~~~~~~~~~~~~~~~~~~~~~~

A common use case is exporting submitted form data to Excel files. Here's a
complete example showing how to create an admin action for exporting data:

.. code-block:: python

    from content_editor.contents import contents_for_items
    from django.utils import timezone
    from feincms3_forms.reporting import get_loaders
    from xlsxdocument import XLSXDocument

    def export_submissions(modeladmin, request, queryset):
        submissions = list(queryset.select_related("configured_form"))
        configured_forms = {sub.configured_form for sub in submissions}

        # Get loaders for all configured forms
        cf_contents = contents_for_items(configured_forms, plugins=renderer.plugins())
        loaders = {cf: get_loaders(contents) for cf, contents in cf_contents.items()}

        cf_values = {}
        for submission in submissions:
            line = [
                {"label": "ID", "name": "", "value": submission.id},
                {"label": "Email", "name": "", "value": submission.email},
                {"label": "Created", "name": "", "value": submission.created_at},
            ] + [loader(submission.data) for loader in loaders[submission.configured_form]]

            if submission.configured_form not in cf_values:
                cf_values[submission.configured_form] = [
                    [cell["label"] for cell in line],  # Header row
                ]
            cf_values[submission.configured_form].append([cell["value"] for cell in line])

        # Create Excel file
        xlsx = XLSXDocument()
        for configured_form, values in cf_values.items():
            xlsx.add_sheet(str(configured_form)[:30])
            xlsx.table(None, values)

        return xlsx.to_response("submissions.xlsx")

Add this action to your ModelAdmin:

.. code-block:: python

    @admin.register(Submission)
    class SubmissionAdmin(admin.ModelAdmin):
        actions = [export_submissions]


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
it.


Advanced usage and recipes
===========================

This section contains practical recipes and patterns for common use cases.


Creating compound field types
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Compound fields generate multiple form fields from a single plugin. Here's an
example of a Duration field that creates "from" and "until" date fields:

.. code-block:: python

    from functools import partial
    from django import forms
    from django.db import models
    from feincms3_forms.models import FormFieldBase, simple_loader

    class Duration(FormFieldBase, ConfiguredFormPlugin):
        label_from = models.CharField("from label", max_length=1000)
        label_until = models.CharField("until label", max_length=1000)

        class Meta:
            verbose_name = "duration"

        def __str__(self):
            return f"{self.label_from} - {self.label_until}"

        def get_fields(self, **kwargs):
            return {
                f"{self.name}_from": forms.DateField(
                    label=self.label_from,
                    required=True,
                    widget=forms.DateInput(attrs={"type": "date"}),
                ),
                f"{self.name}_until": forms.DateField(
                    label=self.label_until,
                    required=True,
                    widget=forms.DateInput(attrs={"type": "date"}),
                ),
            }

        def get_loaders(self):
            return [
                partial(simple_loader, label=self.label_from, name=f"{self.name}_from"),
                partial(simple_loader, label=self.label_until, name=f"{self.name}_until"),
            ]


Creating file upload fields
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

File upload fields require special handling for display and storage:

.. code-block:: python

    from django import forms
    from django.db import models
    from django.conf import settings
    from feincms3_forms.models import FormField

    class UploadFileInput(forms.FileInput):
        template_name = "forms/upload_file_input.html"

        def format_value(self, value):
            return value

        def get_context(self, name, value, attrs):
            if value:
                attrs["required"] = False
            context = super().get_context(name, None, attrs)
            if value and not isinstance(value, File):
                context["current_value"] = os.path.basename(value)
            return context

    class Upload(FormField, ConfiguredFormPlugin):
        class Meta:
            verbose_name = "upload field"

        def get_fields(self, **kwargs):
            return super().get_fields(
                form_class=forms.FileField,
                widget=UploadFileInput,
                **kwargs
            )

        def get_loaders(self):
            def loader(data):
                row = {"label": self.label, "name": self.name}
                if value := data.get(self.name):
                    row["value"] = f"{settings.DOMAIN}{uploads_storage.url(value)}"
                else:
                    row["value"] = ""
                return row

            return [loader]

The corresponding template (``forms/upload_file_input.html``):

.. code-block:: html+django

    {% load i18n %}
    <input type="file" name="{{ widget.name }}"{% include "django/forms/widgets/attrs.html" %}>
    {% if widget.current_value %}
        <p>{% trans "Current file:" %} {{ widget.current_value }}</p>
    {% endif %}


Custom form validation with phone numbers
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Create custom form field classes for specialized validation:

.. code-block:: python

    import phonenumbers
    from django import forms
    from feincms3_forms.models import FormField

    class PhoneNumberFormField(forms.CharField):
        def clean(self, value):
            value = super().clean(value)
            if not value:
                return value

            try:
                number = phonenumbers.parse(value, "CH")
            except phonenumbers.NumberParseException as exc:
                raise forms.ValidationError(str(exc))
            else:
                if phonenumbers.is_valid_number(number):
                    return phonenumbers.format_number(
                        number, phonenumbers.PhoneNumberFormat.E164
                    )
                raise forms.ValidationError("Phone number invalid.")

    class PhoneNumber(FormField, ConfiguredFormPlugin):
        class Meta:
            verbose_name = "phone number field"

        def get_fields(self, **kwargs):
            return super().get_fields(form_class=PhoneNumberFormField, **kwargs)


Grouping form fields with collapsible sections
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Create collapsible groups for better form organization:

.. code-block:: python

    class Group(ConfiguredFormPlugin):
        subregion = "group"

        title = models.CharField(
            "title",
            max_length=200,
            blank=True,
            help_text="Use an empty title to finish an existing group without starting a new one.",
        )

        class Meta:
            verbose_name = "group"

        def __str__(self):
            return self.title

Register it in the renderer:

.. code-block:: python

    renderer.register(models.Group, "")

Handle groups in your view using a custom Regions class:

.. code-block:: python

    from feincms3.regions import Regions, matches
    from feincms3.renderer import render_in_context

    class FormRegions(Regions):
        def handle_group(self, items, context):
            group = items.popleft()
            if not group.title:
                # Terminate group without creating output
                return []

            content = []
            while items and not matches(items[0], subregions={"group"}):
                content.append(
                    self.renderer.render_plugin_in_context(items.popleft(), context)
                )
            return render_in_context(
                context,
                "forms/group.html",
                {"group": group, "content": content}
            )

    # In your view:
    context["form_regions"] = FormRegions.from_contents(contents, renderer=renderer)


Storing submitted data with file handling
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Save file uploads properly when storing form submissions:

.. code-block:: python

    from django.core.files import File
    from app.storage import uploads_storage

    def save_files(instance, form):
        """Extract files from form data and save them to storage."""
        data = form.cleaned_data.copy()
        for key, value in data.items():
            if isinstance(value, File):
                data[key] = uploads_storage.save(
                    f"{instance._meta.label_lower}/{instance.pk}/{value.name}",
                    value,
                )
        return data

    def process_form(request, form, *, configured_form):
        instance = MyModel.objects.create(
            email=form.cleaned_data["email"],
            configured_form=configured_form,
        )
        instance.data = save_files(instance, form)
        instance.save()


Sending email notifications with submission data
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Send formatted emails to managers when forms are submitted:

.. code-block:: python

    from content_editor.contents import contents_for_item
    from feincms3_forms.reporting import get_loaders, value_default
    from authlib.email import render_to_mail

    def send_notifications_to_managers(data, *, configured_form, url=""):
        recipients = configured_form.send_notifications_to or [
            row[1] for row in settings.MANAGERS
        ]

        contents = contents_for_item(configured_form, plugins=renderer.plugins())
        loaders = get_loaders(contents)
        values = [value_default(loader(data)) for loader in loaders]

        mail = render_to_mail(
            "forms/notification_mail",
            {
                "configured_form": configured_form,
                "values": values,
                "url": url
            },
            to=recipients,
        )
        mail.send()

Email template (``forms/notification_mail.txt``):

.. code-block:: text

    A new {{ configured_form.name }} has been submitted.

    {% for value in values %}
    {{ value.label }}: {{ value.value }}
    {% endfor %}

    {% if url %}View in admin: {{ url }}{% endif %}


Continue later functionality for multi-step forms
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Allow users to save progress and continue filling out forms later:

.. code-block:: python

    from django.core import signing

    # In your ConfiguredForm model:
    class ConfiguredForm(forms_models.ConfiguredForm):
        FORMS = [
            forms_models.FormType(
                key="grant-proposal",
                label="grant proposal",
                regions=[Region(key="form", title="form")],
                form_class="app.forms.forms.GrantProposalForm",
                process="app.forms.forms.process_grant_proposal_form",
                allow_continue_later=True,  # Enable continue later
            ),
        ]

    # In your Proposal model:
    def get_proposal_url(self):
        return reverse_app(
            "forms-grant-proposal",
            "code",
            kwargs={"code": signing.dumps(self.pk)},
        )

    # In your view:
    def form(request, code=None):
        context = page_context(request)
        cf = context["page"].form

        form_kwargs = {"request": request, "prefix": short_prefix(cf, "form")}

        if code is not None:
            with contextlib.suppress(Exception):
                form_kwargs["instance"] = Proposal.objects.get(pk=signing.loads(code))

        # ... rest of view code

    # In your form processing:
    def process_grant_proposal_form(request, form, *, configured_form):
        form.instance.proposal = form.instance.proposal | save_files(form.instance, form)
        form.instance.save()

        if "_continue" in request.POST:
            messages.success(
                request,
                "The proposal has been saved. You may continue editing it later.",
            )
            return HttpResponseRedirect(form.instance.get_proposal_url())

        messages.success(request, "The proposal has been sent.")
        # Send notifications...

Template button for "Continue later":

.. code-block:: html+django

    <button type="submit" name="_submit">{% trans "Submit" %}</button>
    {% if configured_form.type.allow_continue_later %}
        <button type="submit" name="_continue">{% trans "Save and continue later" %}</button>
    {% endif %}


Displaying submission data in Django admin
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Show formatted submission data in the admin interface:

.. code-block:: python

    from django.contrib import admin
    from django.contrib.admin import display
    from content_editor.contents import contents_for_item
    from feincms3_forms.reporting import simple_report

    @admin.register(Proposal)
    class ProposalAdmin(admin.ModelAdmin):
        def get_fields(self, request, obj=None):
            fields = super().get_fields(request, obj)
            # Exclude raw JSON fields from the form
            return [field for field in fields if field not in {"outline", "proposal"}]

        def get_readonly_fields(self, request, obj=None):
            return [field.name for field in self.model._meta.fields] + [
                "pretty_outline",
                "pretty_proposal",
            ]

        @display(description="outline")
        def pretty_outline(self, obj):
            return simple_report(
                contents=contents_for_item(
                    obj.outline_form,
                    plugins=renderer.plugins()
                ),
                data=obj.outline,
            )

        @display(description="proposal")
        def pretty_proposal(self, obj):
            return simple_report(
                contents=contents_for_item(
                    obj.proposal_form,
                    plugins=renderer.plugins()
                ),
                data=obj.proposal,
            )


Dynamic regions with database-driven structure
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Create form regions dynamically based on database content. This is useful for
building questionnaires where the structure is entirely configurable via the
admin:

.. code-block:: python

    from content_editor.models import Region
    from admin_ordering.models import OrderableModel

    class ConfiguredForm(forms_models.ConfiguredForm):
        FORMS = [
            forms_models.FormType(
                key="questionnaire",
                label="questionnaire",
                # Regions are dynamically generated from database
                regions=lambda cf: [
                    Region(key="cover", title="Cover"),
                ] + [group.region for group in cf.groups.all()],
                form_class="app.tools.forms.Form",
                process="app.forms.forms.process_questionnaire_form",
            ),
        ]

    class Group(OrderableModel):
        parent = models.ForeignKey(
            ConfiguredForm,
            on_delete=models.CASCADE,
            related_name="groups",
        )
        title = models.CharField(max_length=200)

        @property
        def region(self):
            return Region(
                key=f"group_{self.pk}",
                title=self.title,
            )

In the admin, add an inline for managing groups:

.. code-block:: python

    from admin_ordering.admin import OrderableAdmin

    class GroupInline(OrderableAdmin, admin.TabularInline):
        model = models.Group
        extra = 0

    @admin.register(models.ConfiguredForm)
    class ConfiguredFormAdmin(ConfiguredFormAdmin):
        inlines = [GroupInline, ...other inlines...]


Rendering forms with different regions
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Render only specific regions of a form, useful for multi-page forms:

.. code-block:: python

    def start(request):
        cf = get_configured_form()

        # Only render the first region (cover page)
        contents = contents_for_item(
            cf,
            plugins=renderer.plugins(),
            regions=cf.regions[:1],  # Only first region
        )
        form = create_form(contents, form_class=cf.type.form_class, form_kwargs={...})

        if form.is_valid():
            # Save and redirect to main questionnaire
            return HttpResponseRedirect(...)

    def questionnaire(request):
        cf = get_configured_form()

        # Render remaining regions (skip cover)
        contents = contents_for_item(
            cf,
            plugins=renderer.plugins(),
            regions=cf.regions[1:],  # Skip first region
        )
        form = create_form(contents, form_class=cf.type.form_class, form_kwargs={...})


Custom subregions and nested plugin handling
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Subregions allow you to group related plugins together and handle them as a unit.
This is useful for creating nested structures like accordions, tabs, or hierarchical
form groups.

Example: Create a custom renderer that groups form fields under collapsible headings:

.. code-block:: python

    from feincms3.renderer import RegionRenderer, render_in_context

    class CustomFormRenderer(RegionRenderer):
        def handle_groupitems(self, plugins, context):
            """Collect all items in a groupitems subregion."""
            items = [
                self.render_plugin(plugin, context)
                for plugin in self.takewhile_subregion(plugins, "groupitems")
            ]
            if items:
                yield render_in_context(
                    context,
                    "forms/group-items.html",
                    {"items": items}
                )

        def handle_groupheaders(self, plugins, context):
            """Handle group headers and their nested items."""
            header = plugins.popleft()
            items = self.handle_groupitems(plugins, context)

            if items:
                yield render_in_context(
                    context,
                    "forms/group.html",
                    {"header": header, "items": items}
                )

    renderer = CustomFormRenderer()
    renderer.register(
        models.GroupHeader,
        lambda p, c: {"plugin": p},
        subregion="groupheaders"
    )
    renderer.register(
        models.SimpleField,
        template_renderer("forms/simple-field.html", simple_field_context),
        subregion="groupitems"
    )

This pattern allows you to create forms where plugins are automatically grouped
under headers, with custom rendering for each level of nesting. The key methods
are ``takewhile_subregion()`` which collects plugins until it encounters a
different subregion, and ``handle_<subregion>()`` methods which are automatically
called by the renderer


Multiple renderers for different views
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Use different renderers for form input vs. viewing submitted data:

.. code-block:: python

    # Form renderer for data entry
    form_renderer = RegionRenderer()
    form_renderer.register(
        models.SimpleField,
        template_renderer("forms/simple-field.html", simple_field_context),
    )

    # Report renderer for viewing submitted data
    def report_simple_field_context(plugin, context):
        return {
            "plugin": plugin,
            "rows": [
                loader(context["submission"].data)
                for loader in plugin.get_loaders()
            ],
        }

    report_renderer = RegionRenderer()
    report_renderer.register(
        models.SimpleField,
        template_renderer("forms/report-simple-field.html", report_simple_field_context),
    )

    # In views:
    def questionnaire(request):
        contents = contents_for_item(cf, plugins=form_renderer.plugins())
        form = create_form(contents, ...)

    def report(request, submission):
        contents = contents_for_item(cf, plugins=report_renderer.plugins())
        context["report_regions"] = report_renderer.regions_from_contents(contents)


Signed URLs for secure submission access
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Use Django's signing framework to create secure, tamper-proof URLs for accessing
submissions without authentication:

.. code-block:: python

    from django.core.signing import Signer

    _signer = Signer(salt="submissions")

    class SubmissionQuerySet(models.QuerySet):
        def get_by_code(self, code):
            return self.get(pk=_signer.unsign(code))

    class Submission(models.Model):
        # ... fields ...
        objects = SubmissionQuerySet.as_manager()

        def get_report_url(self):
            return reverse_app(
                "forms",
                "report",
                kwargs={"code": _signer.sign(self.pk)}
            )

    # View decorator for handling signed submissions
    def signed_submission(func):
        @wraps(func)
        def view(request, **kwargs):
            if "code" not in kwargs:
                return func(request, **kwargs)
            try:
                submission = Submission.objects.get_by_code(kwargs.pop("code"))
            except Submission.DoesNotExist:
                messages.error(request, "The submission does not exist.")
            except Exception:
                messages.error(request, "The link is invalid.")
            else:
                return func(request, submission=submission, **kwargs)
            return HttpResponseRedirect("../../../")
        return view

    # Use in views
    @signed_submission
    def report(request, submission):
        # submission is automatically loaded from the signed code
        ...


Admin actions with object-level actions
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Add custom actions to individual objects in the admin using django-object-actions:

.. code-block:: python

    from django_object_actions import DjangoObjectActions

    @admin.register(models.Submission)
    class SubmissionAdmin(DjangoObjectActions, admin.ModelAdmin):
        change_actions = ["view_report"]

        @admin.display(description="View report")
        def view_report(self, request, obj):
            return HttpResponseRedirect(obj.get_report_url())

This adds a "View report" button at the top of the change form for each submission.


Incremental form data merging
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Merge form data incrementally across multiple form submissions (useful for
multi-page forms):

.. code-block:: python

    def process_step_one(request, form, *, configured_form):
        submission = Submission.objects.create(
            title=form.cleaned_data["title"],
            email=form.cleaned_data["email"],
            configured_form=configured_form,
            data={},
        )
        # Save initial data
        submission.data = save_files(submission, form)
        submission.save()
        return HttpResponseRedirect(submission.get_next_step_url())

    def process_step_two(request, form, *, submission):
        # Merge new data with existing data using | operator
        submission.data = submission.data | save_files(submission, form)
        submission.save()
        return HttpResponseRedirect(submission.get_report_url())

The merge operator (``|``) ensures that data from previous steps is preserved
while new fields are added or updated.


Custom validation with HTML5 pattern attribute
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Add client-side validation patterns to form fields:

.. code-block:: python

    class PhoneNumberFormField(forms.CharField):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            # Add HTML5 pattern for client-side validation
            self.widget.attrs.setdefault(
                "pattern",
                r"^[\+\(\)\s]*[0-9][\+\(\)0-9\s]*$"
            )

        def clean(self, value):
            value = super().clean(value)
            if not value:
                return value

            try:
                number = phonenumbers.parse(value, "CH")
            except phonenumbers.NumberParseException as exc:
                raise forms.ValidationError(
                    _("Unable to parse as phone number.")
                ) from exc
            else:
                if phonenumbers.is_valid_number(number):
                    return phonenumbers.format_number(
                        number, phonenumbers.PhoneNumberFormat.E164
                    )
                raise forms.ValidationError(_("Phone number invalid."))

This provides immediate feedback to users before server-side validation.


Conditional inlines based on form type
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Show different inlines in the admin depending on the selected form type:

.. code-block:: python

    from admin_ordering.admin import OrderableAdmin

    class StepInline(OrderableAdmin, admin.TabularInline):
        model = models.Step
        extra = 0

    @admin.register(models.ConfiguredForm)
    class ConfiguredFormAdmin(ConfiguredFormAdmin):
        def get_inlines(self, request, obj):
            if not obj:
                return []

            # Base inlines for all form types
            inlines = [
                ContentEditorInline.create(models.RichText),
                SimpleFieldInline.create(models.Text),
                SimpleFieldInline.create(models.Email),
                # ... more inlines
            ]

            # Add type-specific inlines
            if obj.type.key == "consulting":
                return [StepInline, *inlines]

            return inlines

This allows different form types to have different configuration options.


Advanced process function with validation control
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Create process functions that receive the validation state and control behavior
based on whether the form is partially or fully submitted:

.. code-block:: python

    def process_form(
        request,
        form,
        is_valid,
        *,
        configured_form,
        submission,
        viewname="form",
        is_last=False,
    ):
        # Ensure we have a submission for intermediate steps
        if not is_last and not submission:
            return HttpResponseBadRequest()

        if not submission:
            submission = Submission.objects.create(
                configured_form=configured_form,
                data={},
                email=form.cleaned_data.get("email", ""),
            )

        # Always save data, even if validation failed (for auto-save)
        submission.data = submission.data | save_files(submission, form)
        submission.email = submission.data.get("email") or submission.email
        submission.save()

        # Send notification only on final valid submission
        if is_last and is_valid and (email := submission.data.get("email")):
            mail = render_to_mail(
                "forms/notification_mail",
                {"submission": submission},
                to=[email],
                bcc=["admin@example.com"],
            )
            mail.send(fail_silently=True)

        namespaces = (request.resolver_match.namespaces[-1], "forms")
        url = reverse_app(
            namespaces,
            viewname,
            kwargs={"code": submission._code},
        )
        return HttpResponseRedirect(url)

Call this from your view:

.. code-block:: python

    def form(request, submission):
        # ... form setup ...

        if request.method == "POST":
            should_continue = request.POST.get("_continue")
            is_valid = form.is_valid()

            return cf.type.process(
                request,
                form,
                is_valid,
                configured_form=cf,
                submission=submission,
                viewname="form" if should_continue else "thanks",
                is_last=not should_continue,
            )


Handling DELETE requests for submissions
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Allow users to delete their submissions via AJAX:

.. code-block:: python

    from django.http import JsonResponse

    @signed_submission
    def form(request, submission):
        # ... existing GET/POST handling ...

        if request.method == "DELETE":
            if submission:
                submission.delete()
            return JsonResponse({})

        # ... render form ...

Client-side JavaScript:

.. code-block:: javascript

    // Delete submission button
    deleteButton.addEventListener('click', async () => {
        await fetch(window.location.href, { method: 'DELETE' });
        window.location.href = '/';
    });


Safe filename handling with PurePath
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Use ``pathlib.PurePath`` for secure filename extraction from paths:

.. code-block:: python

    from pathlib import PurePath

    class UploadFileInput(forms.FileInput):
        template_name = "forms/upload_file_input.html"

        def get_context(self, name, value, attrs):
            if value:
                attrs["required"] = False
            context = super().get_context(name, None, attrs)
            if value and not isinstance(value, File):
                # Safely extract filename without directory traversal
                context["current_value"] = PurePath(value).name
            return context

``PurePath`` handles paths safely regardless of the operating system and
prevents directory traversal attacks.
