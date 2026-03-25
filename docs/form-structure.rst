Form structure
==============

This chapter covers how to organise and render forms — grouping fields,
building multi-page flows, and adapting the admin interface.


Collapsible sections
---------------------

Group form fields under collapsible headings using the subregion mechanism:

.. code-block:: python

    class Group(ConfiguredFormPlugin):
        subregion = "group"

        title = models.CharField(
            "title",
            max_length=200,
            blank=True,
            help_text=(
                "Use an empty title to finish an existing group "
                "without starting a new one."
            ),
        )

        class Meta:
            verbose_name = "group"

        def __str__(self):
            return self.title

    renderer.register(models.Group, "")

Handle groups in a custom ``Regions`` class:

.. code-block:: python

    from feincms3.regions import Regions, matches
    from feincms3.renderer import render_in_context

    class FormRegions(Regions):
        def handle_group(self, items, context):
            group = items.popleft()
            if not group.title:
                return []

            content = []
            while items and not matches(items[0], subregions={"group"}):
                content.append(
                    self.renderer.render_plugin_in_context(items.popleft(), context)
                )
            return render_in_context(
                context, "forms/group.html", {"group": group, "content": content}
            )

    # In your view:
    context["form_regions"] = FormRegions.from_contents(contents, renderer=renderer)


Dynamic regions from the database
------------------------------------

Build form regions dynamically from a related model — useful for fully
configurable questionnaires:

.. code-block:: python

    from content_editor.models import Region
    from admin_ordering.models import OrderableModel

    class ConfiguredForm(forms_models.ConfiguredForm):
        FORMS = [
            forms_models.FormType(
                key="questionnaire",
                label="questionnaire",
                regions=lambda cf: [
                    Region(key="cover", title="Cover"),
                ] + [group.region for group in cf.groups.all()],
                form_class="app.tools.forms.Form",
                process="app.forms.forms.process_questionnaire_form",
            ),
        ]

    class Group(OrderableModel):
        parent = models.ForeignKey(
            ConfiguredForm, on_delete=models.CASCADE, related_name="groups"
        )
        title = models.CharField(max_length=200)

        @property
        def region(self):
            return Region(key=f"group_{self.pk}", title=self.title)

Add an inline for managing groups in the admin:

.. code-block:: python

    from admin_ordering.admin import OrderableAdmin

    class GroupInline(OrderableAdmin, admin.TabularInline):
        model = models.Group
        extra = 0

    @admin.register(models.ConfiguredForm)
    class ConfiguredFormAdmin(ConfiguredFormAdmin):
        inlines = [GroupInline, ...]


Rendering specific regions (multi-page forms)
----------------------------------------------

Render only a subset of a form's regions for step-by-step forms:

.. code-block:: python

    def start(request):
        cf = get_configured_form()
        contents = contents_for_item(cf, plugins=renderer.plugins(), regions=cf.regions[:1])
        form = create_form(contents, form_class=cf.type.form_class, form_kwargs={...})

        if form.is_valid():
            return HttpResponseRedirect(...)

    def questionnaire(request):
        cf = get_configured_form()
        contents = contents_for_item(cf, plugins=renderer.plugins(), regions=cf.regions[1:])
        form = create_form(contents, form_class=cf.type.form_class, form_kwargs={...})


Multiple renderers (form input vs. report view)
------------------------------------------------

Use separate renderers for data entry and viewing submitted data:

.. code-block:: python

    # Form renderer for data entry
    form_renderer = RegionRenderer()
    form_renderer.register(
        models.SimpleField,
        template_renderer("forms/simple-field.html", simple_field_context),
    )

    # Report renderer for viewing submitted data
    def report_simple_field_context(plugin, context):
        return {
            "plugin": plugin,
            "rows": [loader(context["submission"].data) for loader in plugin.get_loaders()],
        }

    report_renderer = RegionRenderer()
    report_renderer.register(
        models.SimpleField,
        template_renderer("forms/report-simple-field.html", report_simple_field_context),
    )


Conditional inlines by form type
----------------------------------

Show different admin inlines depending on the selected form type:

.. code-block:: python

    @admin.register(models.ConfiguredForm)
    class ConfiguredFormAdmin(ConfiguredFormAdmin):
        def get_inlines(self, request, obj):
            if not obj:
                return []

            inlines = [
                ContentEditorInline.create(models.RichText),
                SimpleFieldInline.create(models.Text),
                SimpleFieldInline.create(models.Email),
            ]

            if obj.type.key == "consulting":
                return [StepInline, *inlines]

            return inlines
