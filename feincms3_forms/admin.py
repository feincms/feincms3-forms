from content_editor.admin import ContentEditor, ContentEditorInline
from django.core.exceptions import ImproperlyConfigured
from django.utils.translation import gettext_lazy as _


class ConfiguredFormAdmin(ContentEditor):
    pass


class SimpleFieldInline(ContentEditorInline):
    def get_queryset(self, request):
        return super().get_queryset(request).filter(type=self.model.TYPE)

    def get_fieldsets(self, request, obj=None):
        T = self.model.Type
        if self.model.TYPE in {T.TEXT, T.TEXTAREA}:
            core = ["label", "key", "is_required"]
            advanced = ["help_text", "placeholder", "default_value", "max_length"]

        elif self.model.TYPE in {T.EMAIL, T.URL, T.DATE}:
            core = ["label", "key", "is_required"]
            advanced = ["help_text", "placeholder", "default_value"]

        elif self.model.TYPE in {T.CHECKBOX}:
            core = ["label", "key", "is_required"]
            advanced = ["help_text", "default_value"]

        elif self.model.TYPE in {T.SELECT, T.RADIO}:
            core = ["label", "key", "is_required", "choices"]
            advanced = ["help_text", "default_value"]

        else:
            raise ImproperlyConfigured(f"Unknown type {self.model.TYPE}")

        return [
            (None, {"fields": core + ["ordering", "region"]}),
            (_("Advanced"), {"fields": advanced, "classes": ["collapse"]}),
        ]
