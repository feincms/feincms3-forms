from content_editor.models import Region
from django import forms
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.utils.translation import gettext_lazy as _

from feincms3_forms.validation import Error


def validate_contact_form(form):
    keys = set(form.testapp_simplefield_set.values_list("key", flat=True))

    if "email" not in keys:
        yield Error(_('"email" key is missing'))


def process_contact_form(request, form):
    print("Sending mail to", form.cleaned_data)
    messages.success(request, _("Successfully sent the mail (not really!)"))
    return HttpResponseRedirect(".")


class ContactForm(forms.Form):
    regions = [Region(key="form", title=_("form"))]


class OtherFieldsForm(forms.Form):
    email = forms.EmailField()
