from itertools import chain

from django import forms
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.utils.translation import gettext_lazy as _
from testapp.models import ConfiguredFormPlugin

from feincms3_forms.validation import Error, concrete_descendant_instances


def validate_contact_form(form):
    instances = concrete_descendant_instances(ConfiguredFormPlugin)
    keys = set(
        chain.from_iterable(
            (field.key for field in fields) for fields in instances.values()
        )
    )

    if "email" not in keys:
        yield Error(_('"email" key is missing'))


def process_contact_form(request, form):
    print("Sending mail to", form.cleaned_data)
    messages.success(request, _("Successfully sent the mail (not really!)"))
    return HttpResponseRedirect(".")


class OtherFieldsForm(forms.Form):
    email = forms.EmailField()
