from content_editor.contents import contents_for_item
from django.shortcuts import render
from feincms3.renderer import RegionRenderer, template_renderer

from feincms3_forms.renderer import create_form, short_prefix
from testapp.models import ConfiguredForm, Duration, Honeypot, PlainText, SimpleField


def simple_field_context(plugin, context):
    return {"plugin": plugin, "fields": context["form"].get_form_fields(plugin)}


renderer = RegionRenderer()
renderer.register(
    PlainText,
    lambda plugin, context: plugin.text,
)
renderer.register(
    SimpleField,
    template_renderer("forms/simple-field.html", simple_field_context),
)
renderer.register(
    Duration,
    template_renderer("forms/simple-field.html", simple_field_context),
)
renderer.register(
    Honeypot,
    template_renderer("forms/simple-field.html", simple_field_context),
)


def form(request):
    context = {}
    cf = ConfiguredForm.objects.first()

    contents = contents_for_item(cf, plugins=renderer.plugins())

    form_kwargs = {"prefix": short_prefix(cf, "form")}
    if request.method == "POST":
        form_kwargs |= {"data": request.POST, "files": request.FILES}

    form = create_form(
        contents["form"],
        form_class=cf.type.form_class,
        form_kwargs=form_kwargs,
    )

    if form.is_valid():
        return cf.type.process(request, form, configured_form=cf)

    context["form"] = form
    context["form_other_fields"] = form.get_form_fields(None)
    context["form_regions"] = renderer.regions_from_contents(contents)

    return render(request, "forms/form.html", context)
