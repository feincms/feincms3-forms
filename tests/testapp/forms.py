from content_editor.models import Region
from django import forms
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.utils.translation import gettext_lazy as _

from feincms3_forms.validation import Error


class ContactForm(forms.Form):
    regions = [Region(key="form", title=_("form"))]

    @classmethod
    def validate(cls, form):
        keys = set(form.testapp_simplefield_set.values_list("key", flat=True))

        if "email" not in keys:
            yield Error(_('"email" key is missing'))

    def process(self, request):
        print("Sending mail to", self.cleaned_data)
        messages.success(request, _("Successfully sent the mail (not really!)"))
        return HttpResponseRedirect(".")


class OtherFieldsForm(forms.Form):
    email = forms.EmailField()
