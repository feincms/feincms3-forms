from content_editor.admin import ContentEditorInline
from django.contrib import admin

from feincms3_forms.admin import ConfiguredFormAdmin, SimpleFieldInline

from . import models


@admin.register(models.ConfiguredForm)
class ConfiguredFormAdmin(ConfiguredFormAdmin):
    # list_display = ["title"]
    # list_filter = ["is_active", "language_code"]
    # list_per_page = 250
    # prepopulated_fields = {"slug": ["title"]}
    radio_fields = {
        # "menu": admin.HORIZONTAL,
        # "language_code": admin.HORIZONTAL,
        # "page_type": admin.HORIZONTAL,
    }
    # raw_id_fields = ["translation_of"]

    inlines = [
        ContentEditorInline.create(
            model=models.PlainText,
            button='<i class="material-icons">notes</i>',
        ),
        SimpleFieldInline.create(
            model=models.Text,
            button='<i class="material-icons">short_text</i>',
        ),
        SimpleFieldInline.create(
            model=models.Email,
            button='<i class="material-icons">alternate_email</i>',
        ),
        SimpleFieldInline.create(
            model=models.URL,
            button='<i class="material-icons">link</i>',
        ),
        SimpleFieldInline.create(
            model=models.Date,
            button='<i class="material-icons">event</i>',
        ),
        SimpleFieldInline.create(
            model=models.Integer,
            button='<i class="material-icons">looks_one</i>',
        ),
        SimpleFieldInline.create(
            model=models.Textarea,
            button='<i class="material-icons">notes</i>',
        ),
        SimpleFieldInline.create(
            model=models.Checkbox,
            button='<i class="material-icons">check_box</i>',
        ),
        SimpleFieldInline.create(
            model=models.Select,
            button='<i class="material-icons">arrow_drop_down_circle</i>',
        ),
        SimpleFieldInline.create(
            model=models.Radio,
            button='<i class="material-icons">radio_button_checked</i>',
        ),
        SimpleFieldInline.create(models.SelectMultiple),
        SimpleFieldInline.create(models.CheckboxSelectMultiple),
        SimpleFieldInline.create(models.Anything),
        ContentEditorInline.create(model=models.Duration),
    ]

    class Media:
        css = {"all": ["https://fonts.googleapis.com/icon?family=Material+Icons"]}
