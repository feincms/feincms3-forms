from content_editor.models import create_plugin_base
from django import forms
from django.db import models
from django.utils.translation import gettext_lazy as _

from feincms3_forms import models as forms_models


class ConfiguredForm(forms_models.ConfiguredForm):
    FORMS = [
        {
            "key": "contact",
            "label": _("contact form"),
            "form_class": "testapp.forms.ContactForm",
        },
        {
            "key": "other-fields",
            "label": _("other fields"),
            "form_class": "testapp.forms.OtherFieldsForm",
        },
    ]


ConfiguredFormPlugin = create_plugin_base(ConfiguredForm)


class PlainText(ConfiguredFormPlugin):
    text = models.TextField(_("text"))

    class Meta:
        verbose_name = _("text")

    def __str__(self):
        return self.text[:40]


class SimpleField(forms_models.SimpleFieldBase, ConfiguredFormPlugin):
    pass


Text = SimpleField.proxy(SimpleField.Type.TEXT)
Email = SimpleField.proxy(SimpleField.Type.EMAIL)
URL = SimpleField.proxy(SimpleField.Type.URL)
Date = SimpleField.proxy(SimpleField.Type.DATE)
Textarea = SimpleField.proxy(SimpleField.Type.TEXTAREA)
Checkbox = SimpleField.proxy(SimpleField.Type.CHECKBOX)
Select = SimpleField.proxy(SimpleField.Type.SELECT)
Radio = SimpleField.proxy(SimpleField.Type.RADIO)


class CaptchaField(ConfiguredFormPlugin):
    class Meta:
        abstract = True


class Duration(ConfiguredFormPlugin):
    label_from = models.CharField(_("from label"), max_length=1000)
    label_until = models.CharField(_("until label"), max_length=1000)
    key = models.SlugField(
        _("key"),
        help_text=_(
            "Data is saved using this key. Changing it may result in data loss."
        ),
    )

    class Meta:
        verbose_name = _("duration")

    def __str__(self):
        return f"{self.label_from} - {self.label_until}"

    def get_fields(self, **kwargs):
        return {
            f"{self.key}_from": forms.DateField(
                label=self.label_from,
                required=True,
                widget=forms.DateInput(attrs={"type": "date"}),
            ),
            f"{self.key}_until": forms.DateField(
                label=self.label_until,
                required=True,
                widget=forms.DateInput(attrs={"type": "date"}),
            ),
        }


class HoneypotField(forms.CharField):
    widget = forms.HiddenInput

    def validate(self, value):
        if value:
            raise forms.ValidationError(f"Invalid honeypot value {repr(value)}")


class Honeypot(ConfiguredFormPlugin):
    def get_fields(self, **kwargs):
        return {"honeypot": HoneypotField()}
