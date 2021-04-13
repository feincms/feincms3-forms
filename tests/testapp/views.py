from content_editor.contents import contents_for_item
from django.shortcuts import render
from feincms3.regions import Regions
from feincms3.renderer import TemplatePluginRenderer
from testapp.models import ConfiguredForm, Duration, Honeypot, PlainText, SimpleField

from feincms3_forms.renderer import create_form, short_prefix, simple_field_context


renderer = TemplatePluginRenderer()
renderer.register_string_renderer(
    PlainText,
    lambda plugin: plugin.text,
)
renderer.register_template_renderer(
    SimpleField,
    "forms/simple-field.html",
    simple_field_context,
)
renderer.register_template_renderer(
    Duration,
    "forms/simple-field.html",
    simple_field_context,
)
renderer.register_template_renderer(
    Honeypot,
    "forms/simple-field.html",
    simple_field_context,
)


def form(request):
    context = {}
    cf = ConfiguredForm.objects.first()

    contents = contents_for_item(cf, plugins=renderer.plugins())

    form_kwargs = {"prefix": short_prefix(cf, "form")}
    if request.method == "POST":
        form_kwargs.update({"data": request.POST, "files": request.FILES})

    form = create_form(
        contents["form"],
        context=context,
        form_class=cf.form_class,
        form_kwargs=form_kwargs,
    )

    if form.is_valid():
        return form.process(request)

    context.update(
        {
            "form": form,
            "form_regions": Regions.from_contents(contents, renderer=renderer),
            "form_other_fields": form.get_form_fields(None),
        }
    )

    return render(request, "forms/form.html", context)
