from functools import partial

from content_editor.models import Type
from django import forms
from django.core import validators
from django.core.exceptions import ImproperlyConfigured
from django.db import models
from django.db.models import signals
from django.db.models.fields import BLANK_CHOICE_DASH
from django.utils.module_loading import import_string
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _
from feincms3.utils import ChoicesCharField, validation_error


def import_if_string(obj_or_path):
    return import_string(obj_or_path) if isinstance(obj_or_path, str) else obj_or_path


class ImportDescriptor:
    def __set_name__(self, owner, name):
        self._name = name

    def __get__(self, obj, type=None):
        return import_if_string(obj.get(self._name))


class FormType(Type):
    _REQUIRED = {"key", "label", "regions", "form_class", "validate"}

    def __init__(self, **kwargs):
        kwargs.setdefault("form_class", forms.Form)
        kwargs.setdefault("validate", lambda configured_form: [])
        super().__init__(**kwargs)

    form_class = ImportDescriptor()
    process = ImportDescriptor()
    validate = ImportDescriptor()


class ConfiguredForm(models.Model):
    name = models.CharField(_("name"), max_length=1000)
    form = ChoicesCharField(_("form"), max_length=100)

    class Meta:
        abstract = True
        ordering = ["name"]
        verbose_name = _("configured form")
        verbose_name_plural = _("configured form")

    def __str__(self):
        return self.name

    @property
    def regions(self):
        try:
            regions = self.type.regions
        except (AttributeError, KeyError):
            return []
        return regions(self) if callable(regions) else regions

    @staticmethod
    def fill_form_choices(sender, **kwargs):
        if issubclass(sender, ConfiguredForm) and not sender._meta.abstract:
            field = sender._meta.get_field("form")
            field.choices = [(row["key"], row["label"]) for row in sender.FORMS]

            types = {type.key: type for type in sender.FORMS}
            sender.type = property(lambda self: import_if_string(types[self.form]))

    def get_formfields_union(self, *, plugins, values=["name"]):
        qs = None
        for plugin in plugins:
            if not issubclass(plugin, FormField):
                continue
            plugin_qs = plugin.objects.filter(parent=self).values_list(
                *values, flat=len(values) == 1
            )
            if qs is None:
                qs = plugin_qs
            else:
                qs = qs.union(plugin_qs)
        return qs


signals.class_prepared.connect(ConfiguredForm.fill_form_choices)


class NameField(models.CharField):
    def __init__(self, **kwargs):
        kwargs.setdefault("verbose_name", _("name"))
        kwargs.setdefault("max_length", 50)
        kwargs.setdefault(
            "validators",
            [
                validators.RegexValidator(
                    r"^[a-z0-9_]+$",
                    message=_(
                        "Enter a value consisting only of lowercase letters,"
                        " numbers and the underscore."
                    ),
                ),
            ],
        )
        kwargs.setdefault(
            "help_text",
            _(
                "Data is saved using this name. Changing it may result in data loss."
                " This field only allows a-z, 0-9 and _ as characters."
            ),
        )
        super().__init__(**kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        return name, "django.db.models.CharField", args, kwargs


class FormField(models.Model):
    label = models.CharField(_("label"), max_length=1000)
    name = NameField()
    is_required = models.BooleanField(_("is required"), default=True)
    help_text = models.CharField(
        _("help text"),
        max_length=1000,
        blank=True,
    )

    class Meta:
        abstract = True

    def __str__(self):
        return self.label

    def get_fields(self, *, form_class, **kwargs):
        kwargs.setdefault("label", self.label)
        kwargs.setdefault("required", self.is_required)
        kwargs.setdefault("help_text", self.help_text)
        return {self.name: form_class(**kwargs)}

    def get_loaders(self):
        return [partial(simple_loader, label=self.label, name=self.name)]


def simple_loader(data, *, label, name):
    return {"label": label, "name": name, "value": data.get(name)}


class SimpleFieldBase(FormField):
    class Type(models.TextChoices):
        TEXT = "text", _("text field")
        EMAIL = "email", _("email address field")
        URL = "url", _("URL field")
        DATE = "date", _("date field")
        INTEGER = "integer", _("integer field")
        TEXTAREA = "textarea", _("multiline text field")
        CHECKBOX = "checkbox", _("checkbox field")
        SELECT = "select", _("dropdown field")
        RADIO = "radio", _("radio input field")

    type = models.CharField(_("type"), max_length=1000, editable=False)

    choices = models.TextField(
        _("choices"),
        help_text=_("Enter one choice per line."),
    )
    placeholder = models.CharField(
        _("placeholder"),
        max_length=1000,
        blank=True,
    )
    default_value = models.CharField(
        _("default value"),
        max_length=1000,
        blank=True,
        help_text=_("Optional default value of the field."),
    )
    max_length = models.PositiveIntegerField(_("max length"), blank=True, null=True)

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        self.type = self.TYPE
        super().save(*args, **kwargs)

    save.alters_data = True

    @classmethod
    def proxy(cls, type_name, **meta):
        meta["proxy"] = True
        meta["app_label"] = cls._meta.app_label

        if "verbose_name" not in meta and hasattr(type_name, "label"):
            meta["verbose_name"] = type_name.label

        meta_class = type("Meta", (cls.Meta,), meta)

        cls = type(
            f"{cls.__qualname__}_{type_name}",
            (cls,),
            {"__module__": cls.__module__, "Meta": meta_class},
        )
        cls.TYPE = type_name
        return cls

    def clean_fields(self, exclude=None):
        super().clean_fields(exclude)

        if self.choices and self.default_value:
            if slugify(self.default_value) not in dict(self.get_choices()):
                raise validation_error(
                    _(
                        'The specified default value "%(default)s" isn\'t part of'
                        " the available choices."
                    )
                    % {"default": self.default_value},
                    field="default_value",
                    exclude=exclude,
                )

    def get_choices(self):
        def _choice(value):
            parts = [part.strip() for part in value.split("|", 1)]
            if len(parts) == 1:
                return (slugify(value), value)
            else:
                return tuple(parts)

        return [_choice(value) for value in self.choices.splitlines() if value]

    def get_initial(self):
        if not self.default_value:
            return {}
        if self.choices:
            return {self.name: slugify(self.default_value)}
        return {self.name: self.default_value}

    def get_fields(self, **kwargs):
        T = self.Type

        if self.type == T.TEXT:
            return super().get_fields(
                form_class=forms.CharField,
                max_length=self.max_length,
                widget=forms.CharField.widget(
                    attrs={"placeholder": self.placeholder or False}
                ),
            )

        elif self.type == T.EMAIL:
            return super().get_fields(
                form_class=forms.EmailField,
                widget=forms.EmailField.widget(
                    attrs={"placeholder": self.placeholder or False}
                ),
            )

        elif self.type == T.URL:
            return super().get_fields(
                form_class=forms.URLField,
                widget=forms.URLField.widget(
                    attrs={"placeholder": self.placeholder or False}
                ),
            )

        elif self.type == T.DATE:
            return super().get_fields(
                form_class=forms.DateField,
                widget=forms.DateInput(
                    attrs={"placeholder": self.placeholder or False, "type": "date"}
                ),
            )

        elif self.type == T.INTEGER:
            return super().get_fields(
                form_class=forms.IntegerField,
                widget=forms.IntegerField.widget(
                    attrs={"placeholder": self.placeholder or False}
                ),
            )

        elif self.type == T.TEXTAREA:
            return super().get_fields(
                form_class=forms.CharField,
                max_length=self.max_length,
                widget=forms.Textarea(
                    attrs={
                        "maxlength": self.max_length or False,
                        "placeholder": self.placeholder or False,
                        "rows": 5,
                    },
                ),
            )

        elif self.type == T.CHECKBOX:
            return super().get_fields(form_class=forms.BooleanField)

        elif self.type == T.SELECT:
            choices = self.get_choices()
            if not self.is_required or not self.default_value:
                choices = BLANK_CHOICE_DASH + choices
            return super().get_fields(
                form_class=forms.ChoiceField,
                choices=choices,
            )

        elif self.type == T.RADIO:
            return super().get_fields(
                form_class=forms.ChoiceField,
                widget=forms.RadioSelect,
                choices=self.get_choices(),
            )

        else:  # pragma: no cover
            raise ImproperlyConfigured(f"Unknown type {self.model.TYPE}")
