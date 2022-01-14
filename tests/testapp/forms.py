from django import forms
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.utils.translation import gettext_lazy as _
from testapp.models import Log
from testapp.views import renderer

from feincms3_forms.validation import validate_required_fields, validate_uniqueness


def validate_contact_form(configured_form):
    names = list(configured_form.get_formfields_union(plugins=renderer.plugins()))
    return [
        *validate_uniqueness(names),
        *validate_required_fields(names, {"email"}),
    ]


def process_contact_form(request, form, *, configured_form):
    messages.success(request, _("Successfully sent the mail (not really!)"))
    Log.objects.create(configured_form=configured_form, data=form.cleaned_data)
    return HttpResponseRedirect(".")


class OtherFieldsForm(forms.Form):
    email = forms.EmailField()
