from urllib.parse import quote as urlquote

from content_editor.admin import ContentEditor, ContentEditorInline
from django.contrib import messages
from django.contrib.admin.utils import quote
from django.core.exceptions import ImproperlyConfigured
from django.urls import reverse
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _


NO_CONTINUE_PARAMETERS = {"_addanother", "_save", "_saveasnew"}


class ConfiguredFormAdmin(ContentEditor):
    # Possible hook for validation, with stack hacking: _create_formsets

    def validate_configured_form(self, request, obj):
        if type := obj.type:
            for msg in type.validate(obj):
                msg.add_to(request)

        opts = obj._meta
        obj_url = reverse(
            "admin:%s_%s_change" % (opts.app_label, opts.model_name),
            args=(quote(obj.pk),),
            current_app=self.admin_site.name,
        )
        if self.has_change_permission(request, obj):
            obj_repr = format_html('<a href="{}">{}</a>', urlquote(obj_url), obj)
        else:
            obj_repr = str(obj)
        messages.info(
            request, format_html(_('"{obj}" has been validated.'), obj=obj_repr)
        )

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change=change)
        if request.method == "POST" and any(
            key in request.POST for key in NO_CONTINUE_PARAMETERS
        ):
            self.validate_configured_form(request, form.instance)

    def render_change_form(self, request, context, *, obj, **kwargs):
        if obj and request.method == "GET":
            self.validate_configured_form(request, obj)
        return super().render_change_form(request, context, obj=obj, **kwargs)


class SimpleFieldInline(ContentEditorInline):
    def get_queryset(self, request):
        return super().get_queryset(request).filter(type=self.model.TYPE)

    def get_fieldsets(self, request, obj=None):
        T = self.model.Type
        if self.model.TYPE in {T.TEXT, T.TEXTAREA}:
            core = ["label", "key", "is_required"]
            advanced = ["help_text", "placeholder", "default_value", "max_length"]

        elif self.model.TYPE in {T.EMAIL, T.URL, T.DATE, T.INTEGER}:
            core = ["label", "key", "is_required"]
            advanced = ["help_text", "placeholder", "default_value"]

        elif self.model.TYPE in {T.CHECKBOX}:
            core = ["label", "key", "is_required"]
            advanced = ["help_text", "default_value"]

        elif self.model.TYPE in {T.SELECT, T.RADIO}:
            core = ["label", "key", "is_required", "choices"]
            advanced = ["help_text", "default_value"]

        else:  # pragma: no cover
            raise ImproperlyConfigured(f"Unknown type {self.model.TYPE}")

        return [
            (None, {"fields": core + ["ordering", "region"]}),
            (_("Advanced"), {"fields": advanced, "classes": ["collapse"]}),
        ]
