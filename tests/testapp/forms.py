from django import forms
from django.http import HttpResponseRedirect
from testapp.models import Log
from testapp.views import renderer

from feincms3_forms.validation import (
    validate_required_fields,
    validate_types,
    validate_uniqueness,
)


def validate_contact_form(configured_form):
    fields = configured_form.get_formfields_union(
        plugins=renderer.plugins(), attributes=["type"]
    )
    field_types = {field[0]: field[1] for field in fields}
    return [
        *validate_uniqueness(fields),
        *validate_required_fields(fields, {"email"}),
        *validate_types(field_types, {"email": "email"}),
    ]


def process_contact_form(request, form, *, configured_form):
    Log.objects.create(configured_form=configured_form, data=form.cleaned_data)
    return HttpResponseRedirect(".")


class OtherFieldsForm(forms.Form):
    email = forms.EmailField()
