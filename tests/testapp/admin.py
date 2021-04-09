from django.contrib import admin

from . import models


@admin.register(models.Model)
class ModelAdmin(admin.ModelAdmin):
    fieldsets = [models.Model.admin_fieldset()]
