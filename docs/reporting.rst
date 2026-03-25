Reporting and export
====================

This chapter covers how to display and export submitted form data.


Displaying submissions in the admin
-------------------------------------

Use ``simple_report`` to render a formatted summary of submitted data directly
in the Django admin change view:

.. code-block:: python

    from content_editor.contents import contents_for_item
    from django.contrib.admin import display
    from feincms3_forms.reporting import simple_report

    @admin.register(Submission)
    class SubmissionAdmin(admin.ModelAdmin):
        @display(description="Submitted data")
        def pretty_data(self, obj):
            return simple_report(
                contents=contents_for_item(
                    obj.configured_form, plugins=renderer.plugins()
                ),
                data=obj.data,
            )


Exporting submissions to Excel
--------------------------------

.. code-block:: python

    from content_editor.contents import contents_for_items
    from feincms3_forms.reporting import get_loaders
    from xlsxdocument import XLSXDocument

    def export_submissions(modeladmin, request, queryset):
        submissions = list(queryset.select_related("configured_form"))
        configured_forms = {sub.configured_form for sub in submissions}

        cf_contents = contents_for_items(configured_forms, plugins=renderer.plugins())
        loaders = {cf: get_loaders(contents) for cf, contents in cf_contents.items()}

        cf_values = {}
        for submission in submissions:
            line = [
                {"label": "ID", "name": "", "value": submission.id},
                {"label": "Email", "name": "", "value": submission.email},
                {"label": "Created", "name": "", "value": submission.created_at},
            ] + [loader(submission.data) for loader in loaders[submission.configured_form]]

            if submission.configured_form not in cf_values:
                cf_values[submission.configured_form] = [
                    [cell["label"] for cell in line],
                ]
            cf_values[submission.configured_form].append([cell["value"] for cell in line])

        xlsx = XLSXDocument()
        for configured_form, values in cf_values.items():
            xlsx.add_sheet(str(configured_form)[:30])
            xlsx.table(None, values)

        return xlsx.to_response("submissions.xlsx")

    @admin.register(Submission)
    class SubmissionAdmin(admin.ModelAdmin):
        actions = [export_submissions]
