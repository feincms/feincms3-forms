from content_editor.admin import ContentEditorInline
from django.utils.translation import gettext_lazy as _


class SimpleFieldInline(ContentEditorInline):
    fieldsets = [
        (
            None,
            {
                "fields": [
                    "label",
                    "key",
                    "is_required",
                    "ordering",
                    "region",
                ],
            },
        ),
        (
            _("Advanced"),
            {
                "fields": [
                    "help_text",
                    "placeholder",
                    "default_value",
                ],
                "classes": ["collapse"],
            },
        ),
    ]

    def get_queryset(self, request):
        return super().get_queryset(request).filter(type=self.model.TYPE)


class SimpleChoiceFieldInline(ContentEditorInline):
    fieldsets = [
        (
            None,
            {
                "fields": [
                    "label",
                    "key",
                    "is_required",
                    "choices",
                    "ordering",
                    "region",
                ],
            },
        ),
        (
            _("Advanced"),
            {
                "fields": [
                    "help_text",
                    "default_value",
                ],
                "classes": ["collapse"],
            },
        ),
    ]

    def get_queryset(self, request):
        return super().get_queryset(request).filter(type=self.model.TYPE)
