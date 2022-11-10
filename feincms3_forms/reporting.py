from itertools import chain

from django.template.defaultfilters import linebreaksbr, urlize
from django.utils.html import format_html, mark_safe

from feincms3_forms.models import FormFieldBase


def get_loaders(plugins):
    return list(
        chain.from_iterable(
            plugin.get_loaders()
            for plugin in plugins
            if isinstance(plugin, FormFieldBase)
        )
    )


def value_default(row, default="Ø"):
    return row if row["value"] else (row | {"value": default})


def simple_report(*, contents, data):
    def _prettify(row):
        return row | {"pretty": linebreaksbr(urlize(row["value"]))}

    loaders = get_loaders(contents)
    return mark_safe(
        "<br>\n".join(
            format_html(
                "<p><strong>{label}</strong> ({name})</p> <p>{pretty}</p>",
                **_prettify(value_default(loader(data))),
            )
            for loader in loaders
        )
    )
