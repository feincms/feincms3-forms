from functools import reduce
from hashlib import sha1
from operator import or_

from django import forms


def short_prefix(obj, postfix=""):
    identifier = f"{obj._meta.label}:{obj.pk}:{postfix}"
    return sha1(identifier.encode("utf-8")).hexdigest()[:6]


class FormMixin:
    def get_form_fields(self, item):
        return self._f3f_item_fields[item]


def create_form(items, *, form_class=forms.Form, form_kwargs):
    item_fields = {
        item: item.get_fields() for item in items if hasattr(item, "get_fields")
    }
    all_fields = reduce(or_, item_fields.values(), {})
    all_names = set(all_fields)

    initial = reduce(
        or_, (item.get_initial() for item in items if hasattr(item, "get_initial")), {}
    )
    form_kwargs["initial"] = initial | form_kwargs.get("initial", {})

    form = type("Form", (FormMixin, form_class), all_fields)(**form_kwargs)
    form._f3f_item_fields = {
        item: {name: form[name] for name in fields}
        for item, fields in item_fields.items()
    } | {None: {name: form[name] for name in form.fields if name not in all_names}}

    return form
