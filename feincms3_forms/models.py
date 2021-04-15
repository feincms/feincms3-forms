from content_editor.models import Type
from django import forms
from django.db import models
from django.db.models import signals
from django.db.models.fields import BLANK_CHOICE_DASH
from django.utils.module_loading import import_string
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _
from feincms3.mixins import ChoicesCharField
from feincms3.utils import validation_error


class FormType(Type):
    _REQUIRED = {"key", "label", "form_class"}


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
            return self.form_class.regions
        except (AttributeError, KeyError):
            return []

    @staticmethod
    def fill_form_choices(sender, **kwargs):
        if issubclass(sender, ConfiguredForm) and not sender._meta.abstract:
            field = sender._meta.get_field("form")
            field.choices = [(row["key"], row["label"]) for row in sender.FORMS]

            form_classes = {row["key"]: row["form_class"] for row in sender.FORMS}
            sender.form_class = property(
                lambda self: import_string(form_classes[self.form])
            )


signals.class_prepared.connect(ConfiguredForm.fill_form_choices)


class SimpleFieldBase(models.Model):
    class Type(models.TextChoices):
        TEXT = "text", _("text field")
        EMAIL = "email", _("email address field")
        URL = "url", _("URL field")
        DATE = "date", _("date field")
        TEXTAREA = "textarea", _("multiline text field")
        CHECKBOX = "checkbox", _("checkbox field")
        SELECT = "select", _("dropdown field")
        RADIO = "radio", _("radio input field")

    type = models.CharField(_("type"), max_length=1000, editable=False)

    label = models.CharField(_("label"), max_length=1000)
    key = models.SlugField(
        _("key"),
        help_text=_(
            "Data is saved using this key. Changing it may result in data loss."
        ),
    )
    is_required = models.BooleanField(_("is required"), default=True)
    help_text = models.CharField(
        _("help text"),
        max_length=1000,
        blank=True,
    )

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

    def __str__(self):
        return self.label

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

    def get_fields(self, *, initial=None, **kwargs):
        T = self.Type

        if self.default_value and initial is not None:
            if self.choices:
                initial.setdefault(self.key, slugify(self.default_value))
            else:
                initial.setdefault(self.key, self.default_value)

        field_kw = {
            "label": self.label,
            "required": self.is_required,
            "help_text": self.help_text,
        }

        if self.type == T.TEXTAREA:
            return {
                self.key: forms.CharField(
                    max_length=self.max_length,
                    widget=forms.Textarea(
                        attrs={
                            "maxlength": self.max_length or False,
                            "placeholder": self.placeholder or False,
                            "rows": 5,
                        },
                    ),
                    **field_kw,
                )
            }

        elif self.type == T.DATE:
            return {
                self.key: forms.DateField(
                    widget=forms.DateInput(
                        attrs={"placeholder": self.placeholder or False, "type": "date"}
                    ),
                    **field_kw,
                )
            }

        elif self.type == T.RADIO:
            return {
                self.key: forms.ChoiceField(
                    widget=forms.RadioSelect(), choices=self.get_choices(), **field_kw
                ),
            }

        elif self.type == T.SELECT:
            choices = self.get_choices()
            if not self.is_required or not self.default_value:
                choices = BLANK_CHOICE_DASH + choices
            return {
                self.key: forms.ChoiceField(choices=choices, **field_kw),
            }

        elif self.type in {T.EMAIL, T.URL}:
            field = {
                T.EMAIL: forms.EmailField,
                T.URL: forms.URLField,
            }[self.type]
            return {
                self.key: field(
                    widget=field.widget(
                        attrs={"placeholder": self.placeholder or False}
                    ),
                    **field_kw,
                ),
            }

        elif self.type == T.CHECKBOX:
            return {
                self.key: forms.BooleanField(**field_kw),
            }

        else:
            field = forms.CharField
            return {
                self.key: field(
                    max_length=self.max_length,
                    widget=field.widget(
                        attrs={"placeholder": self.placeholder or False}
                    ),
                    **field_kw,
                ),
            }
