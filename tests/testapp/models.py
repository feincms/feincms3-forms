from functools import partial

from content_editor.models import Region, create_plugin_base
from django import forms
from django.core.serializers.json import DjangoJSONEncoder
from django.db import models
from django.utils.translation import gettext_lazy as _

from feincms3_forms import models as forms_models


class ConfiguredForm(forms_models.ConfiguredForm):
    FORMS = [
        forms_models.FormType(
            key="contact",
            label=_("contact form"),
            regions=[Region(key="form", title=_("form"))],
            validate="testapp.forms.validate_contact_form",
            process="testapp.forms.process_contact_form",
        ),
        forms_models.FormType(
            key="other-fields",
            label=_("other fields"),
            regions=[],
            form_class="testapp.forms.OtherFieldsForm",
        ),
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
Integer = SimpleField.proxy(SimpleField.Type.INTEGER)
Textarea = SimpleField.proxy(SimpleField.Type.TEXTAREA)
Checkbox = SimpleField.proxy(SimpleField.Type.CHECKBOX)
Select = SimpleField.proxy(SimpleField.Type.SELECT)
Radio = SimpleField.proxy(SimpleField.Type.RADIO, verbose_name="Listen to the radio")
SelectMultiple = SimpleField.proxy(SimpleField.Type.SELECT_MULTIPLE)
CheckboxSelectMultiple = SimpleField.proxy(SimpleField.Type.CHECKBOX_SELECT_MULTIPLE)


def clean_duration(form, data, *, name):
    from_name = f"{name}_from"
    until_name = f"{name}_until"
    if (f := data.get(from_name)) and (u := data.get(until_name)) and f > u:
        form.add_error(until_name, "Until has to be later than from.")
    return data


class Duration(forms_models.FormFieldBase, ConfiguredFormPlugin):
    label_from = models.CharField(_("from label"), max_length=1000)
    label_until = models.CharField(_("until label"), max_length=1000)

    class Meta:
        verbose_name = _("duration")

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

    def get_cleaners(self):
        return [partial(clean_duration, name=self.name)]


class HoneypotField(forms.CharField):
    widget = forms.HiddenInput

    def validate(self, value):
        super().validate(value)
        if value:
            raise forms.ValidationError(f"Invalid honeypot value {repr(value)}")


class Honeypot(forms_models.FormFieldBase, ConfiguredFormPlugin):
    name = forms_models.NameField(default="honeypot")

    class Meta:
        verbose_name = _("honeypot")

    def get_fields(self, **kwargs):
        return {self.name: HoneypotField(required=False)}


class Log(models.Model):
    configured_form = models.ForeignKey(ConfiguredForm, on_delete=models.CASCADE)
    data = models.JSONField(encoder=DjangoJSONEncoder)
