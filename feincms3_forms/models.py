from content_editor.models import Region
from django import forms
from django.db import models
from django.db.models import signals
from django.utils.text import capfirst, slugify
from django.utils.translation import gettext_lazy as _
from feincms3.mixins import ChoicesCharField
from feincms3.utils import validation_error


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
        except KeyError:
            return []

    @staticmethod
    def fill_form_choices(sender, **kwargs):
        if issubclass(sender, ConfiguredForm) and not sender._meta.abstract:
            field = sender._meta.get_field("form")
            field.choices = [(row["key"], row["label"]) for row in sender.FORMS]

            form_classes = {row["key"]: row["form_class"] for row in sender.FORMS}
            sender.form_class = property(lambda self: form_classes[self.form])


signals.class_prepared.connect(ConfiguredForm.fill_form_choices)


class FormBase(forms.Form):
    regions = [Region(key="form", title=capfirst(_("form")))]

    @classmethod
    def validate(cls, form):
        pass


class FieldBase(models.Model):
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

    class Meta:
        abstract = True

    def __str__(self):
        return self.label


class SimpleFieldMixin(models.Model):
    type = models.CharField(_("type"), max_length=1000, editable=False)

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
        meta_class = type("Meta", (cls.Meta,), meta)

        cls = type(
            f"{cls.__qualname__}_{type_name}",
            (cls,),
            {"__module__": cls.__module__, "Meta": meta_class},
        )
        cls.TYPE = type_name
        return cls


class SimpleFieldBase(FieldBase, SimpleFieldMixin):
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

    class Meta:
        abstract = True

    def get_fields(self, **kwargs):
        if self.default_value and "initial" in kwargs:
            kwargs["initial"].setdefault(self.key, self.default_value)

        field_kw = {
            "label": self.label,
            "required": self.is_required,
            "help_text": self.help_text,
        }

        if self.type == "textarea":
            return {
                self.key: forms.CharField(
                    widget=forms.Textarea(
                        attrs={"placeholder": self.placeholder, "rows": 5}
                    ),
                    **field_kw,
                )
            }

        elif self.type == "date":
            return {
                self.key: forms.DateField(
                    widget=forms.DateInput(
                        attrs={"placeholder": self.placeholder, "type": "date"}
                    ),
                    **field_kw,
                )
            }

        else:
            field = {
                "text": forms.CharField,
                "email": forms.EmailField,
                "checkbox": forms.BooleanField,
            }.get(self.type, forms.CharField)
            return {
                self.key: field(
                    widget=field.widget(attrs={"placeholder": self.placeholder}),
                    **field_kw,
                ),
            }


class SimpleChoiceFieldBase(FieldBase, SimpleFieldMixin):
    choices = models.TextField(
        _("choices"),
        help_text=_("Enter one choice per line."),
    )
    default_value = models.CharField(
        _("default value"),
        max_length=1000,
        blank=True,
        help_text=_("Optional default value of the field."),
    )

    class Meta:
        abstract = True

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
        return [(slugify(value), value) for value in self.choices.splitlines()]

    def get_fields(self, **kwargs):
        if self.default_value and "initial" in kwargs:
            kwargs["initial"].setdefault(self.key, slugify(self.default_value))

        choices = self.get_choices()
        field_kw = {
            "label": self.label,
            "required": self.is_required,
            "help_text": self.help_text,
            "choices": choices,
        }

        if self.type == "radio":
            return {
                self.key: forms.ChoiceField(widget=forms.RadioSelect(), **field_kw),
            }

        else:
            if not self.is_required or self.default_value:
                choices = [("", "----------")] + choices

            return {
                self.key: forms.ChoiceField(**field_kw),
            }
