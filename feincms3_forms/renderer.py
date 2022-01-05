from functools import reduce
from hashlib import sha1
from operator import add, or_

from django import forms

from feincms3_forms.models import FormFieldBase


def short_prefix(obj, part=""):
    identifier = f"{obj._meta.label}:{obj.pk}:{part}".encode()
    return "form-" + sha1(identifier).hexdigest()[:5]


class FormMixin:
    def get_form_fields(self, item):
        return self._f3f_item_fields[item]

    def clean(self):
        data = super().clean()
        for hook in self._f3f_cleaners:
            data = hook(self, data)
        return data


def create_form(items, *, form_class=forms.Form, form_kwargs):
    field_items = [item for item in items if isinstance(item, FormFieldBase)]
    item_fields = {item: item.get_fields() for item in field_items}
    all_fields = reduce(or_, item_fields.values(), {})
    all_names = set(all_fields)

    initial = reduce(
        or_,
        (item.get_initial() for item in field_items),
        {},
    )
    form_kwargs["initial"] = initial | form_kwargs.get("initial", {})

    form = type("Form", (FormMixin, form_class), all_fields)(**form_kwargs)
    form._f3f_item_fields = {
        item: {name: form[name] for name in fields}
        for item, fields in item_fields.items()
    } | {None: {name: form[name] for name in form.fields if name not in all_names}}
    form._f3f_cleaners = reduce(add, (item.get_cleaners() for item in field_items), [])

    return form
