Recipes
=======

This section contains practical patterns for common use cases.


Compound field types
--------------------

Compound fields generate multiple Django form fields from a single plugin.
Always prefix field names with ``f"{self.name}_"`` to ensure uniqueness across
multiple instances of the same plugin:

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


.. _strip-name-prefix:

Custom templates for compound fields
-------------------------------------

Use the ``strip_name_prefix`` parameter in ``get_form_fields()`` to access
compound field values by their short names (without the plugin name prefix)
inside templates:

.. code-block:: python

    class AddressBlock(FormFieldBase, ConfiguredFormPlugin):
        def get_fields(self):
            return {
                f"{self.name}_first_name": forms.CharField(label="First name"),
                f"{self.name}_last_name": forms.CharField(label="Last name"),
                f"{self.name}_street": forms.CharField(label="Street"),
                f"{self.name}_postal_code": forms.CharField(label="Postal code"),
                f"{self.name}_city": forms.CharField(label="City"),
            }

    renderer.register(
        models.AddressBlock,
        lambda plugin, context: render_in_context(
            context,
            "forms/address-block.html",
            {
                "plugin": plugin,
                "fields": context["form"].get_form_fields(plugin, strip_name_prefix=True),
            },
        ),
    )

Template (``forms/address-block.html``):

.. code-block:: html+django

    <div class="address-block">
      <div class="field field-50-50">
        {{ fields.first_name }}
        {{ fields.last_name }}
      </div>
      <div class="field field-25-75">
        {{ fields.postal_code }}
        {{ fields.city }}
      </div>
    </div>

Without ``strip_name_prefix=True`` you would need ``fields.address_first_name``,
etc.


File upload fields
------------------

File upload fields require a custom widget to handle the case where a file has
already been uploaded (e.g. when re-displaying a form after a validation error):

.. code-block:: python

    import os
    from django import forms
    from django.core.files import File
    from django.db import models
    from django.conf import settings
    from pathlib import PurePath
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
                # PurePath prevents directory traversal attacks
                context["current_value"] = PurePath(value).name
            return context

    class Upload(FormField, ConfiguredFormPlugin):
        class Meta:
            verbose_name = "upload field"

        def get_fields(self, **kwargs):
            return super().get_fields(
                form_class=forms.FileField,
                widget=UploadFileInput,
                **kwargs,
            )

        def get_loaders(self):
            def loader(data):
                row = {"label": self.label, "name": self.name}
                row["value"] = (
                    f"{settings.DOMAIN}{uploads_storage.url(data[self.name])}"
                    if data.get(self.name)
                    else ""
                )
                return row

            return [loader]

Template (``forms/upload_file_input.html``):

.. code-block:: html+django

    {% load i18n %}
    <input type="file" name="{{ widget.name }}"{% include "django/forms/widgets/attrs.html" %}>
    {% if widget.current_value %}
        <p>{% trans "Current file:" %} {{ widget.current_value }}</p>
    {% endif %}


Storing uploaded files
----------------------

When saving a form submission that includes file uploads, move the in-memory
file objects to permanent storage before serialising the data as JSON:

.. code-block:: python

    from django.core.files import File

    def save_files(instance, form):
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


Custom field types with validation
-----------------------------------

Create custom form field classes for specialised validation:

.. code-block:: python

    import phonenumbers
    from django import forms
    from django.utils.translation import gettext_lazy as _
    from feincms3_forms.models import FormField

    class PhoneNumberFormField(forms.CharField):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            # Add HTML5 pattern for immediate client-side feedback
            self.widget.attrs.setdefault(
                "pattern",
                r"^[\+\(\)\s]*[0-9][\+\(\)0-9\s]*$",
            )

        def clean(self, value):
            value = super().clean(value)
            if not value:
                return value
            try:
                number = phonenumbers.parse(value, "CH")
            except phonenumbers.NumberParseException as exc:
                raise forms.ValidationError(_("Unable to parse as phone number.")) from exc
            if phonenumbers.is_valid_number(number):
                return phonenumbers.format_number(
                    number, phonenumbers.PhoneNumberFormat.E164
                )
            raise forms.ValidationError(_("Phone number invalid."))

    class PhoneNumber(FormField, ConfiguredFormPlugin):
        class Meta:
            verbose_name = "phone number field"

        def get_fields(self, **kwargs):
            return super().get_fields(form_class=PhoneNumberFormField, **kwargs)


Collapsible sections
---------------------

Group form fields under collapsible headings using the subregion mechanism:

.. code-block:: python

    class Group(ConfiguredFormPlugin):
        subregion = "group"

        title = models.CharField(
            "title",
            max_length=200,
            blank=True,
            help_text=(
                "Use an empty title to finish an existing group "
                "without starting a new one."
            ),
        )

        class Meta:
            verbose_name = "group"

        def __str__(self):
            return self.title

    renderer.register(models.Group, "")

Handle groups in a custom ``Regions`` class:

.. code-block:: python

    from feincms3.regions import Regions, matches
    from feincms3.renderer import render_in_context

    class FormRegions(Regions):
        def handle_group(self, items, context):
            group = items.popleft()
            if not group.title:
                return []

            content = []
            while items and not matches(items[0], subregions={"group"}):
                content.append(
                    self.renderer.render_plugin_in_context(items.popleft(), context)
                )
            return render_in_context(
                context, "forms/group.html", {"group": group, "content": content}
            )

    # In your view:
    context["form_regions"] = FormRegions.from_contents(contents, renderer=renderer)


Dynamic regions from the database
-----------------------------------

Build form regions dynamically from a related model — useful for fully
configurable questionnaires:

.. code-block:: python

    from content_editor.models import Region
    from admin_ordering.models import OrderableModel

    class ConfiguredForm(forms_models.ConfiguredForm):
        FORMS = [
            forms_models.FormType(
                key="questionnaire",
                label="questionnaire",
                regions=lambda cf: [
                    Region(key="cover", title="Cover"),
                ] + [group.region for group in cf.groups.all()],
                form_class="app.tools.forms.Form",
                process="app.forms.forms.process_questionnaire_form",
            ),
        ]

    class Group(OrderableModel):
        parent = models.ForeignKey(
            ConfiguredForm, on_delete=models.CASCADE, related_name="groups"
        )
        title = models.CharField(max_length=200)

        @property
        def region(self):
            return Region(key=f"group_{self.pk}", title=self.title)

Add an inline for managing groups in the admin:

.. code-block:: python

    from admin_ordering.admin import OrderableAdmin

    class GroupInline(OrderableAdmin, admin.TabularInline):
        model = models.Group
        extra = 0

    @admin.register(models.ConfiguredForm)
    class ConfiguredFormAdmin(ConfiguredFormAdmin):
        inlines = [GroupInline, ...]


Rendering specific regions (multi-page forms)
----------------------------------------------

Render only a subset of a form's regions for step-by-step forms:

.. code-block:: python

    def start(request):
        cf = get_configured_form()
        contents = contents_for_item(cf, plugins=renderer.plugins(), regions=cf.regions[:1])
        form = create_form(contents, form_class=cf.type.form_class, form_kwargs={...})

        if form.is_valid():
            return HttpResponseRedirect(...)

    def questionnaire(request):
        cf = get_configured_form()
        contents = contents_for_item(cf, plugins=renderer.plugins(), regions=cf.regions[1:])
        form = create_form(contents, form_class=cf.type.form_class, form_kwargs={...})


Multiple renderers (form input vs. report view)
------------------------------------------------

Use separate renderers for data entry and viewing submitted data:

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
            "rows": [loader(context["submission"].data) for loader in plugin.get_loaders()],
        }

    report_renderer = RegionRenderer()
    report_renderer.register(
        models.SimpleField,
        template_renderer("forms/report-simple-field.html", report_simple_field_context),
    )


Sending email notifications
----------------------------

.. code-block:: python

    from content_editor.contents import contents_for_item
    from feincms3_forms.reporting import get_loaders, value_default

    def send_notifications_to_managers(data, *, configured_form, url=""):
        recipients = configured_form.send_notifications_to or [
            row[1] for row in settings.MANAGERS
        ]

        contents = contents_for_item(configured_form, plugins=renderer.plugins())
        loaders = get_loaders(contents)
        values = [value_default(loader(data)) for loader in loaders]

        mail = render_to_mail(
            "forms/notification_mail",
            {"configured_form": configured_form, "values": values, "url": url},
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


Displaying submissions in the admin
-------------------------------------

.. code-block:: python

    from content_editor.contents import contents_for_item
    from django.contrib.admin import display
    from feincms3_forms.reporting import simple_report

    @admin.register(Submission)
    class SubmissionAdmin(admin.ModelAdmin):
        @display(description="Submitted data")
        def pretty_data(self, obj):
            return simple_report(
                contents=contents_for_item(
                    obj.configured_form, plugins=renderer.plugins()
                ),
                data=obj.data,
            )


Exporting submissions to Excel
--------------------------------

.. code-block:: python

    from content_editor.contents import contents_for_items
    from feincms3_forms.reporting import get_loaders
    from xlsxdocument import XLSXDocument

    def export_submissions(modeladmin, request, queryset):
        submissions = list(queryset.select_related("configured_form"))
        configured_forms = {sub.configured_form for sub in submissions}

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
                    [cell["label"] for cell in line],
                ]
            cf_values[submission.configured_form].append([cell["value"] for cell in line])

        xlsx = XLSXDocument()
        for configured_form, values in cf_values.items():
            xlsx.add_sheet(str(configured_form)[:30])
            xlsx.table(None, values)

        return xlsx.to_response("submissions.xlsx")

    @admin.register(Submission)
    class SubmissionAdmin(admin.ModelAdmin):
        actions = [export_submissions]


Incremental data merging for multi-step forms
----------------------------------------------

Use the dict merge operator to accumulate data across multiple form steps:

.. code-block:: python

    def process_step_one(request, form, *, configured_form):
        submission = Submission.objects.create(
            configured_form=configured_form, data={}
        )
        submission.data = save_files(submission, form)
        submission.save()
        return HttpResponseRedirect(submission.get_next_step_url())

    def process_step_two(request, form, *, submission):
        # | preserves data from previous steps
        submission.data = submission.data | save_files(submission, form)
        submission.save()
        return HttpResponseRedirect(submission.get_report_url())


Continue later (save progress)
--------------------------------

Allow users to save an incomplete form and resume later:

.. code-block:: python

    from django.core import signing

    class ConfiguredForm(forms_models.ConfiguredForm):
        FORMS = [
            forms_models.FormType(
                key="grant-proposal",
                label="grant proposal",
                regions=[Region(key="form", title="form")],
                form_class="app.forms.forms.GrantProposalForm",
                process="app.forms.forms.process_grant_proposal_form",
                allow_continue_later=True,
            ),
        ]

    def process_grant_proposal_form(request, form, *, configured_form):
        form.instance.data = form.instance.data | save_files(form.instance, form)
        form.instance.save()

        if "_continue" in request.POST:
            messages.success(request, "The proposal has been saved.")
            return HttpResponseRedirect(form.instance.get_proposal_url())

        messages.success(request, "The proposal has been sent.")
        # send notifications...

Template submit buttons:

.. code-block:: html+django

    <button type="submit" name="_submit">{% trans "Submit" %}</button>
    {% if configured_form.type.allow_continue_later %}
        <button type="submit" name="_continue">{% trans "Save and continue later" %}</button>
    {% endif %}


Signed URLs for submission access
-----------------------------------

Use Django's signing framework for tamper-proof URLs that don't require
authentication:

.. code-block:: python

    from django.core.signing import Signer

    _signer = Signer(salt="submissions")

    class SubmissionQuerySet(models.QuerySet):
        def get_by_code(self, code):
            return self.get(pk=_signer.unsign(code))

    class Submission(models.Model):
        objects = SubmissionQuerySet.as_manager()

        def get_report_url(self):
            return reverse_app("forms", "report", kwargs={"code": _signer.sign(self.pk)})

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


Conditional inlines by form type
----------------------------------

Show different admin inlines depending on the selected form type:

.. code-block:: python

    @admin.register(models.ConfiguredForm)
    class ConfiguredFormAdmin(ConfiguredFormAdmin):
        def get_inlines(self, request, obj):
            if not obj:
                return []

            inlines = [
                ContentEditorInline.create(models.RichText),
                SimpleFieldInline.create(models.Text),
                SimpleFieldInline.create(models.Email),
            ]

            if obj.type.key == "consulting":
                return [StepInline, *inlines]

            return inlines


JSON plugins with proxy mixins
--------------------------------

For fields whose configuration involves nested data (e.g. an array of choices),
use `django-json-schema-editor
<https://github.com/matthiask/django-json-schema-editor>`_ together with
feincms3-forms proxy models.

The key advantage over regular Django models is that nested data — such as an
array of choice options — can be edited inline without requiring nested inlines
(which Django admin does not support).

**Base class**

.. code-block:: python

    from django_json_schema_editor.plugins import JSONPluginBase
    from feincms3_forms.models import FormFieldBase

    class JSONPlugin(JSONPluginBase, FormFieldBase, ConfiguredFormPlugin):
        pass

**Field mixin**

.. code-block:: python

    class SingleChoiceMixin:
        def get_fields(self):
            return {
                self.name: forms.ChoiceField(
                    widget=forms.RadioSelect,
                    choices=[
                        (choice["name"], mark_safe(choice["description"]))
                        for choice in self.data["choices"]
                    ],
                    label=self.data["label"],
                    required=self.data["is_required"],
                    help_text=self.data.get("help_text", ""),
                )
            }

        def get_loaders(self):
            return [partial(simple_loader, name=self.name, label=self.data["label"])]

**Proxy model with schema**

.. code-block:: python

    SingleChoice = JSONPlugin.proxy(
        "single_choice",
        verbose_name=_("single choice"),
        mixins=[SingleChoiceMixin],
        schema={
            "type": "object",
            "properties": {
                "label": {"type": "string", "title": _("label")},
                "is_required": {
                    "type": "boolean",
                    "title": _("is required"),
                    "format": "checkbox",
                },
                "help_text": {"type": "string", "title": _("help text")},
                "choices": {
                    "type": "array",
                    "format": "table",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string", "title": _("value"), "minLength": 1},
                            "description": {
                                "type": "string",
                                "format": "prose",
                                "title": _("label"),
                            },
                        },
                    },
                },
            },
        },
    )

**Admin integration**

.. code-block:: python

    from django_json_schema_editor.plugins import JSONPluginInline

    @admin.register(models.ConfiguredForm)
    class FormAdmin(ConfiguredFormAdmin):
        inlines = [
            # ... SimpleFieldInline instances ...
            JSONPluginInline.create(model=models.SingleChoice, icon="radio_button_checked"),
        ]

**Template rendering**

Use ``strip_name_prefix=True`` for compound JSON plugin fields:

.. code-block:: python

    renderer.register(
        models.JSONPlugin,
        "",  # base class is not rendered directly
    )
    renderer.register(
        [models.SingleChoice],
        lambda plugin, context: render_in_context(
            context,
            [f"forms/{plugin.type}-field.html", "forms/simple-field.html"],
            {
                "plugin": plugin,
                "fields": context["form"].get_form_fields(plugin, strip_name_prefix=True),
            },
        ),
        fetch=False,
    )

Whether to prefer JSON plugins or regular proxy models is largely a matter of
preference. Both integrate seamlessly with feincms3-forms. JSON plugins are
most useful when field configuration requires nested data that would otherwise
need a separate model and inline.
