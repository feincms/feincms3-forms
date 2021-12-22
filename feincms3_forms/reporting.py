from itertools import chain

from feincms3_forms.models import FormFieldBase


def get_loaders(items):
    return list(
        chain.from_iterable(
            item.get_loaders() for item in items if isinstance(item, FormFieldBase)
        )
    )


def value_default(row, default="Ø"):
    return row if row["value"] else (row | {"value": default})
