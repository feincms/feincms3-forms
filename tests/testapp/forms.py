from content_editor.models import Region
from django import forms
from django.utils.translation import gettext_lazy as _


class ContactForm(forms.Form):
    regions = [Region(key="form", title=_("form"))]


class OtherFieldsForm(forms.Form):
    email = forms.EmailField()
