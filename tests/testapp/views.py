from django.shortcuts import render
from feincms3.renderer import TemplatePluginRenderer
from testapp.models import ConfiguredForm, Duration, PlainText, SimpleField

from feincms3_forms.regions import FormRegions


renderer = TemplatePluginRenderer()
renderer.register_string_renderer(
    PlainText,
    lambda plugin: plugin.text,
)
renderer.register_template_renderer(
    SimpleField,
    "forms/simple-field.html",
)
renderer.register_template_renderer(
    Duration,
    "forms/simple-field.html",
)


def form(request):
    context = {}
    cf = ConfiguredForm.objects.first()

    context["form_regions"] = regions = FormRegions.from_item(cf, renderer=renderer)
    context["form"] = form = regions.get_form(
        items=regions.contents["form"],
        form_class=cf.form_class,
        form_kwargs={"data": request.POST, "files": request.FILES}
        if request.method == "POST"
        else {},
    )

    if form.is_valid():
        return form.process(request)

    return render(request, "forms/form.html", context)
