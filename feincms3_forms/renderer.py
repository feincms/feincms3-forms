from functools import reduce
from hashlib import sha1

from django import forms


F3F_CONTEXT = "_f3f_context"


def short_prefix(obj, postfix=""):
    identifier = f"{obj._meta.label}:{obj.pk}:{postfix}"
    return sha1(identifier.encode("utf-8")).hexdigest()[:6]


def simple_field_context(plugin, context):
    return {"plugin": plugin, "fields": context[F3F_CONTEXT]["item_fields"][plugin]}


def other_fields(context):
    return context[F3F_CONTEXT]["other_fields"]


def create_form(items, *, context, form_class=forms.Form, form_kwargs):
    form_kwargs.setdefault("auto_id", None)
    initial = form_kwargs.setdefault("initial", {})
    item_fields = {}

    for item in items:
        if hasattr(item, "get_fields"):
            item_fields[item] = item.get_fields(initial=initial)

    all_fields = reduce(lambda a, b: {**a, **b}, item_fields.values(), {})

    form = type("Form", (form_class,), all_fields)(**form_kwargs)

    context[F3F_CONTEXT] = {
        "form": form,
        "item_fields": {
            item: {key: form[key] for key in fields}
            for item, fields in item_fields.items()
        },
        "other_fields": {
            key: form[key] for key in form.fields if key not in all_fields
        },
    }

    return form
