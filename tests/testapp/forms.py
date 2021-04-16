from django import forms
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.utils.translation import gettext_lazy as _
from testapp.views import renderer

from feincms3_forms.validation import Error


def validate_contact_form(cf):
    names = list(cf.get_formfields_union(plugins=renderer.plugins()))

    if "email" not in names:
        yield Error(_('Field with a name of "email" is missing.'))


def process_contact_form(request, form):
    print("Sending mail to", form.cleaned_data)
    messages.success(request, _("Successfully sent the mail (not really!)"))
    return HttpResponseRedirect(".")


class OtherFieldsForm(forms.Form):
    email = forms.EmailField()
