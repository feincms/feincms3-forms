from urllib.parse import quote as urlquote

from content_editor.admin import ContentEditor, ContentEditorInline
from django.contrib import messages
from django.contrib.admin.utils import quote
from django.urls import reverse
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _


NO_CONTINUE_PARAMETERS = {"_addanother", "_save", "_saveasnew"}


class ConfiguredFormAdmin(ContentEditor):
    # Possible hook for validation, with stack hacking: _create_formsets

    def validate_configured_form(self, request, obj):
        opts = obj._meta
        obj_url = reverse(
            f"admin:{opts.app_label}_{opts.model_name}_change",
            args=(quote(obj.pk),),
            current_app=self.admin_site.name,
        )
        if self.has_change_permission(request, obj):
            obj_repr = format_html('<a href="{}">{}</a>', urlquote(obj_url), obj)
        else:
            obj_repr = str(obj)

        if type := obj.type:
            if msgs := list(type.validate(obj)):
                messages.warning(
                    request,
                    format_html(
                        _('Validation of "{obj}" wasn\'t completely successful.'),
                        obj=obj_repr,
                    ),
                )
                for msg in msgs:
                    messages.add_message(request, msg.level, msg.message)
            else:
                messages.success(
                    request, format_html(_('"{obj}" has been validated.'), obj=obj_repr)
                )
        else:
            messages.warning(
                request,
                format_html(
                    _(
                        '"{obj}" could not be validated because'
                        " it seems to have an invalid type."
                    ),
                    obj=obj_repr,
                ),
            )

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change=change)
        # Only validate if navigating away from this page. Otherwise validation
        # will happen in render_change_form anyway.
        if request.method == "POST" and any(
            key in request.POST for key in NO_CONTINUE_PARAMETERS
        ):
            self.validate_configured_form(request, form.instance)

    def render_change_form(self, request, context, *, obj, **kwargs):
        if obj and request.method == "GET":
            self.validate_configured_form(request, obj)
        return super().render_change_form(request, context, obj=obj, **kwargs)


class FormFieldInline(ContentEditorInline):
    core_fields = ["name", "label", "is_required"]
    advanced_fields = ["help_text"]

    def get_fieldsets(self, request, obj=None):
        return [
            (None, {"fields": self.core_fields + ["ordering", "region"]}),
            (_("Advanced"), {"fields": self.advanced_fields, "classes": ["collapse"]}),
        ]


class SimpleFieldInline(FormFieldInline):
    def get_queryset(self, request):
        return super().get_queryset(request).filter(type=self.model.TYPE)

    @classmethod
    def create(cls, model, **kwargs):
        T = model.Type
        if model.TYPE in {T.TEXT, T.TEXTAREA}:
            kwargs.setdefault(
                "advanced_fields",
                ["help_text", "placeholder", "default_value", "max_length"],
            )

        elif model.TYPE in {T.EMAIL, T.URL, T.DATE, T.INTEGER}:
            kwargs.setdefault(
                "advanced_fields", ["help_text", "placeholder", "default_value"]
            )

        elif model.TYPE in {T.CHECKBOX}:
            kwargs.setdefault("advanced_fields", ["help_text", "default_value"])

        elif model.TYPE in {T.SELECT}:
            kwargs.setdefault(
                "core_fields", ["name", "label", "is_required", "choices"]
            )
            kwargs.setdefault(
                "advanced_fields", ["help_text", "placeholder", "default_value"]
            )

        elif model.TYPE in {
            T.RADIO,
            T.SELECT_MULTIPLE,
            T.CHECKBOX_SELECT_MULTIPLE,
        }:
            kwargs.setdefault(
                "core_fields", ["name", "label", "is_required", "choices"]
            )
            kwargs.setdefault("advanced_fields", ["help_text", "default_value"])

        return super().create(model, **kwargs)
