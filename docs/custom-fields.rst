Custom field plugins
====================

This chapter covers how to define your own form field plugin types beyond the
built-in ``SimpleFieldBase`` proxies.


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
--------------------------------------

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


Custom field types with validation
------------------------------------

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
