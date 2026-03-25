Handling submissions
====================

This chapter covers everything that happens after a form is submitted:
storing data, notifying stakeholders, supporting multi-step flows, and
letting users resume incomplete submissions.


Storing uploaded files
-----------------------

When saving a form submission that includes file uploads, move the in-memory
file objects to permanent storage before serialising the data as JSON:

.. code-block:: python

    from django.core.files import File

    def save_files(instance, form):
        data = form.cleaned_data.copy()
        for key, value in data.items():
            if isinstance(value, File):
                data[key] = uploads_storage.save(
                    f"{instance._meta.label_lower}/{instance.pk}/{value.name}",
                    value,
                )
        return data

    def process_form(request, form, *, configured_form):
        instance = MyModel.objects.create(
            email=form.cleaned_data["email"],
            configured_form=configured_form,
        )
        instance.data = save_files(instance, form)
        instance.save()


Sending email notifications
-----------------------------

.. code-block:: python

    from content_editor.contents import contents_for_item
    from feincms3_forms.reporting import get_loaders, value_default

    def send_notifications_to_managers(data, *, configured_form, url=""):
        recipients = configured_form.send_notifications_to or [
            row[1] for row in settings.MANAGERS
        ]

        contents = contents_for_item(configured_form, plugins=renderer.plugins())
        loaders = get_loaders(contents)
        values = [value_default(loader(data)) for loader in loaders]

        mail = render_to_mail(
            "forms/notification_mail",
            {"configured_form": configured_form, "values": values, "url": url},
            to=recipients,
        )
        mail.send()

Email template (``forms/notification_mail.txt``):

.. code-block:: text

    A new {{ configured_form.name }} has been submitted.

    {% for value in values %}
    {{ value.label }}: {{ value.value }}
    {% endfor %}

    {% if url %}View in admin: {{ url }}{% endif %}


Incremental data merging for multi-step forms
----------------------------------------------

Use the dict merge operator to accumulate data across multiple form steps:

.. code-block:: python

    def process_step_one(request, form, *, configured_form):
        submission = Submission.objects.create(
            configured_form=configured_form, data={}
        )
        submission.data = save_files(submission, form)
        submission.save()
        return HttpResponseRedirect(submission.get_next_step_url())

    def process_step_two(request, form, *, submission):
        # | preserves data from previous steps
        submission.data = submission.data | save_files(submission, form)
        submission.save()
        return HttpResponseRedirect(submission.get_report_url())


Continue later (save progress)
--------------------------------

Allow users to save an incomplete form and resume later:

.. code-block:: python

    from django.core import signing

    class ConfiguredForm(forms_models.ConfiguredForm):
        FORMS = [
            forms_models.FormType(
                key="grant-proposal",
                label="grant proposal",
                regions=[Region(key="form", title="form")],
                form_class="app.forms.forms.GrantProposalForm",
                process="app.forms.forms.process_grant_proposal_form",
                allow_continue_later=True,
            ),
        ]

    def process_grant_proposal_form(request, form, *, configured_form):
        form.instance.data = form.instance.data | save_files(form.instance, form)
        form.instance.save()

        if "_continue" in request.POST:
            messages.success(request, "The proposal has been saved.")
            return HttpResponseRedirect(form.instance.get_proposal_url())

        messages.success(request, "The proposal has been sent.")
        # send notifications...

Template submit buttons:

.. code-block:: html+django

    <button type="submit" name="_submit">{% trans "Submit" %}</button>
    {% if configured_form.type.allow_continue_later %}
        <button type="submit" name="_continue">{% trans "Save and continue later" %}</button>
    {% endif %}


Signed URLs for submission access
-----------------------------------

Use Django's signing framework for tamper-proof URLs that don't require
authentication:

.. code-block:: python

    from django.core.signing import Signer

    _signer = Signer(salt="submissions")

    class SubmissionQuerySet(models.QuerySet):
        def get_by_code(self, code):
            return self.get(pk=_signer.unsign(code))

    class Submission(models.Model):
        objects = SubmissionQuerySet.as_manager()

        def get_report_url(self):
            return reverse_app("forms", "report", kwargs={"code": _signer.sign(self.pk)})

    def signed_submission(func):
        @wraps(func)
        def view(request, **kwargs):
            if "code" not in kwargs:
                return func(request, **kwargs)
            try:
                submission = Submission.objects.get_by_code(kwargs.pop("code"))
            except Submission.DoesNotExist:
                messages.error(request, "The submission does not exist.")
            except Exception:
                messages.error(request, "The link is invalid.")
            else:
                return func(request, submission=submission, **kwargs)
            return HttpResponseRedirect("../../../")
        return view
