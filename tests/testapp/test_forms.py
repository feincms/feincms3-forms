from content_editor.contents import contents_for_item
from django import forms, test
from django.contrib.auth.models import User
from django.contrib.messages import get_messages
from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.test.utils import isolate_apps

from feincms3_forms.models import FormField, FormFieldBase, FormType
from feincms3_forms.renderer import create_form
from feincms3_forms.reporting import get_loaders, simple_report, value_default
from feincms3_forms.validation import Error, Warning
from testapp.models import (
    URL,
    Anything,
    Checkbox,
    CheckboxSelectMultiple,
    ConfiguredForm,
    Date,
    Duration,
    Email,
    Honeypot,
    Integer,
    Log,
    PlainText,
    Radio,
    Select,
    SelectMultiple,
    Text,
    Textarea,
)


# from django.test.utils import override_settings
# from django.utils.functional import lazy


def messages(response):
    return [m.message for m in get_messages(response.wsgi_request)]


class FormsTest(test.TestCase):
    def test_stuff(self):
        cf = ConfiguredForm.objects.create(name="Test", form_type="contact")
        plugin1 = Text.objects.create(
            parent=cf,
            region="form",
            ordering=10,
            label="Full name",
            name="full_name",
        )
        plugin2 = PlainText.objects.create(
            parent=cf,
            region="form",
            ordering=20,
            text="Something",
        )

        response = self.client.get("/")
        prefix = response.context["form"].prefix
        name = f"{prefix}-full_name"
        self.assertContains(
            response,
            f'<input type="text" name="{name}" id="id_{name}" required>',
            1,
            html=True,
        )

        response = self.client.post("/", {name: "test@example.org"})
        self.assertRedirects(response, "/")
        # print(response, response.content.decode("utf-8"))

        log = Log.objects.get()
        loaders = get_loaders([plugin1, plugin2])
        values = [loader(log.data) for loader in loaders]
        self.assertEqual(
            values,
            [{"label": "Full name", "name": "full_name", "value": "test@example.org"}],
        )
        values = [loader({}) for loader in loaders]
        self.assertEqual(
            values,
            [{"label": "Full name", "name": "full_name", "value": None}],
        )
        values = [value_default(loader({})) for loader in loaders]
        self.assertEqual(
            values,
            [{"label": "Full name", "name": "full_name", "value": "Ø"}],
        )

        report = simple_report(contents=[plugin1, plugin2], data=log.data)
        self.assertEqual(
            report,
            '<p><strong>Full name</strong> (full_name)</p> <p><a href="mailto:test@example.org">test@example.org</a></p>',
        )

    def test_admin_validation_messages(self):
        user = User.objects.create_superuser("admin", "admin@example.com", "password")
        self.client.force_login(user)

        cf = ConfiguredForm.objects.create(name="Test", form_type="contact")
        response = self.client.get(f"/admin/testapp/configuredform/{cf.id}/change/")

        self.assertContains(response, "&quot;testapp_simplefield_set&quot;")
        self.assertContains(response, "&quot;testapp_simplefield_set-2&quot;")
        self.assertContains(response, "&quot;testapp_simplefield_set-8&quot;")
        # print(response, response.content.decode("utf-8"))

        self.assertContains(response, "Validation of ")
        self.assertContains(response, "Required fields are missing: &#x27;email&#x27;.")

        Email.objects.create(
            parent=cf,
            region="form",
            ordering=10,
            label="Email",
            name="email",
        )
        self.assertEqual(list(cf.type.validate(cf)), [])

        Email.objects.create(
            parent=cf,
            region="form",
            ordering=20,
            label="Email",
            name="email",
        )
        self.assertEqual(
            list(cf.type.validate(cf)),
            [Warning("Fields exist more than once: 'email' (2).")],
        )

        data = {
            "name": cf.name,
            "form_type": cf.form_type,
            "testapp_duration_set-TOTAL_FORMS": 0,
            "testapp_duration_set-INITIAL_FORMS": 0,
            "testapp_plaintext_set-TOTAL_FORMS": 0,
            "testapp_plaintext_set-INITIAL_FORMS": 0,
            "testapp_simplefield_set-TOTAL_FORMS": 0,
            "testapp_simplefield_set-INITIAL_FORMS": 0,
        }
        for i in range(20):
            data |= {
                f"testapp_simplefield_set-{i}-TOTAL_FORMS": 0,
                f"testapp_simplefield_set-{i}-INITIAL_FORMS": 0,
            }
        response = self.client.post(
            f"/admin/testapp/configuredform/{cf.id}/change/",
            data,
            fetch_redirect_response=False,
        )
        m = messages(response)
        self.assertEqual(len(m), 1)
        self.assertTrue(m[0].endswith("was changed successfully."))
        self.client.get("/admin/")  # Remove messages

        data["_save"] = 1
        response = self.client.post(
            f"/admin/testapp/configuredform/{cf.id}/change/",
            data,
            fetch_redirect_response=False,
        )
        m = messages(response)
        self.assertEqual(len(m), 3)
        self.assertTrue(m[0].startswith('Validation of "<'))
        self.assertEqual(m[1], "Fields exist more than once: 'email' (2).")
        self.assertTrue(m[2].endswith("was changed successfully."))

    def test_simple_admin_validation(self):
        user = User.objects.create_superuser("admin", "admin@example.com", "password")
        self.client.force_login(user)

        response = self.client.get("/admin/testapp/configuredform/add/")
        self.assertNotContains(response, "has been validated.")

        cf = ConfiguredForm.objects.create(name="Test", form_type="other-fields")
        response = self.client.get(f"/admin/testapp/configuredform/{cf.id}/change/")
        self.assertContains(response, " has been validated.")
        self.assertContains(response, "Listen to the radio")

    def test_invalid_type(self):
        user = User.objects.create_superuser("admin", "admin@example.com", "password")
        self.client.force_login(user)

        cf = ConfiguredForm.objects.create(name="Test", form_type="--notexists--")
        response = self.client.get(f"/admin/testapp/configuredform/{cf.id}/change/")
        self.assertContains(response, "seems to have an invalid type")

    def test_form_without_plugins(self):
        ConfiguredForm.objects.create(name="Test", form_type="contact")
        response = self.client.get("/")
        prefix = response.context["form"].prefix
        self.assertTrue(bool(prefix))

    def test_unconfigured_form(self):
        cf = ConfiguredForm.objects.create()
        self.assertEqual(cf.regions, [])

    def test_choices(self):
        cf = ConfiguredForm.objects.create()
        kw = {
            "parent": cf,
            "region": "form",
            "ordering": 10,
            "label": "label",
            "name": "name",
            "type": "select",
        }

        plugin = Select(choices="a\nb", default_value="", **kw)
        plugin.full_clean()  # Validates just fine
        self.assertEqual(
            plugin.get_fields()["name"].choices,
            [("", "---------"), ("a", "a"), ("b", "b")],
        )

        plugin.default_value = "b"
        plugin.full_clean()  # Validates just fine
        self.assertEqual(
            plugin.get_fields()["name"].choices,
            [("a", "a"), ("b", "b")],
        )

        with self.assertRaises(ValidationError) as cm:
            plugin.default_value = "c"
            plugin.full_clean()

        self.assertEqual(
            cm.exception.error_dict["default_value"][0].message,
            'The specified default value "c" isn\'t part of the available choices.',
        )

        kw["type"] = "radio"

        plugin = Select(choices="A\nB is fun", default_value="", **kw)
        plugin.full_clean()  # Validates just fine

        self.assertEqual(
            plugin.get_fields()["name"].choices,
            [("a", "A"), ("b-is-fun", "B is fun")],
        )
        self.assertNotIn("name", plugin.get_initial())

        plugin.default_value = "B is fun"
        self.assertEqual(plugin.get_initial(), {"name": "b-is-fun"})

        plugin = Select(
            choices="KEY VALUE | pretty label\n OTHER VALUE | other pretty label \n\n",
            default_value="",
            **kw,
        )
        plugin.full_clean()  # Validates just fine
        self.assertEqual(
            plugin.get_fields()["name"].choices,
            [
                ("KEY VALUE", "pretty label"),
                ("OTHER VALUE", "other pretty label"),
            ],
        )

    def test_other_fields(self):
        cf = ConfiguredForm.objects.create(name="Test", form_type="other-fields")
        self.assertEqual(cf.regions, [])

        response = self.client.get("/")
        prefix = response.context["form"].prefix
        name = f"{prefix}-email"
        self.assertContains(
            response,
            f'<input type="email" name="{name}" id="id_{name}" maxlength="320" required>',
            1,
            html=True,
        )

    def test_honeypot(self):
        cf = ConfiguredForm.objects.create(name="Test", form_type="contact")
        Text.objects.create(
            parent=cf,
            region="form",
            ordering=10,
            label="Subject",
            name="subject",
            is_required=False,
        )
        Honeypot.objects.create(
            parent=cf,
            region="form",
            ordering=10,
        )

        self.assertCountEqual(
            cf.get_formfields_union(plugins=[Text, Honeypot]),
            [("subject", {}), ("honeypot", {})],
        )

        response = self.client.get("/")
        prefix = response.context["form"].prefix
        name = f"{prefix}-honeypot"
        self.assertContains(
            response,
            f'<input type="hidden" name="{name}" id="id_{name}">',
            html=True,
        )

        response = self.client.post("/", {f"{prefix}-honeypot": "anything"})
        self.assertContains(response, "Invalid honeypot value")

        response = self.client.post("/", {f"{prefix}-honeypot": ""})
        # print(response, response.content.decode("utf-8"))
        self.assertRedirects(response, "/")

    def test_initial(self):
        """Default values work and can be overridden from the outside"""
        cf = ConfiguredForm.objects.create(name="Test", form_type="contact")
        plugin = Text.objects.create(
            parent=cf,
            region="form",
            ordering=10,
            label="Full name",
            name="full_name",
            default_value="Hans",
        )

        form = create_form(
            [plugin],
            form_kwargs={"auto_id": ""},
        )
        self.assertHTMLEqual(
            str(form["full_name"]),
            '<input type="text" name="full_name" value="Hans" required>',
        )

        form = create_form(
            [plugin], form_kwargs={"auto_id": "", "initial": {"full_name": "Franz"}}
        )
        self.assertHTMLEqual(
            str(form["full_name"]),
            '<input type="text" name="full_name" value="Franz" required>',
        )

    def test_formtype_getattr(self):
        ft = FormType(
            key="required",
            label="required",
            regions="required",
            form_class="required",
            validate="required",
            #
            int=42,
            module="django.test",
            nothing="no.thing",
        )

        self.assertEqual(ft.int, 42)
        self.assertEqual(ft.module, test)
        self.assertEqual(ft.nothing, "no.thing")

    def test_simplefield_str(self):
        f = Text(label=" ".join("abc" for _ in range(100)))
        self.assertEqual(str(f), "abc abc abc abc abc abc abc abc abc abc abc abc a…")

    def test_cleaners(self):
        cf = ConfiguredForm.objects.create(name="Test", form_type="contact")
        Duration.objects.create(
            parent=cf,
            region="form",
            name="duration",
            ordering=10,
            label_from="from",
            label_until="until",
        )

        self.assertCountEqual(
            cf.get_formfields_union(plugins=[Duration]),
            [("duration", {})],
        )

        response = self.client.get("/")
        prefix = response.context["form"].prefix
        from_name = f"{prefix}-duration_from"
        until_name = f"{prefix}-duration_until"

        response = self.client.post(
            "/",
            {
                from_name: "2022-01-06",
                until_name: "2022-01-01",
            },
        )
        # print(response, response.content.decode("utf-8"))
        self.assertContains(response, "Until has to be later than from.")

        response = self.client.post(
            "/",
            {
                from_name: "2022-01-06",
                until_name: "2022-01-10",
            },
        )
        self.assertRedirects(response, "/")

    def test_automatic_name(self):
        field = Text()._meta.get_field("name")

        name = field.to_python("name")
        self.assertEqual(name, "name")

        name = field.to_python("")
        self.assertTrue(name.startswith("field_"))

        name = field.to_python(None)
        self.assertTrue(name.startswith("field_"))

        # Very improbable
        self.assertNotEqual(field.to_python(""), field.to_python(""))

    def test_validation_message(self):
        w = Warning("Hello")
        self.assertEqual(str(w), "Hello")
        self.assertEqual(repr(w), "<Warning: message='Hello'>")

    def test_get_formfields_union(self):
        cf = ConfiguredForm.objects.create(name="Test", form_type="contact")
        Text.objects.create(
            parent=cf,
            region="form",
            ordering=10,
            label="Full name",
            name="full_name",
        )
        PlainText.objects.create(
            parent=cf,
            region="form",
            ordering=20,
            text="Something",
        )
        Honeypot.objects.create(
            parent=cf,
            region="form",
            ordering=30,
        )
        Duration.objects.create(
            parent=cf,
            region="form",
            name="duration",
            ordering=40,
            label_from="from",
            label_until="until",
        )

        self.assertCountEqual(
            cf.get_formfields_union(
                plugins=[Text, PlainText, Honeypot, Duration],
                attributes=[
                    "type",
                    "label",
                    "label_from",
                    "region",
                    "ordering",
                    "is_required",
                ],
            ),
            [
                (
                    "full_name",
                    {
                        "type": "text",
                        "label": "Full name",
                        "label_from": "",
                        "region": "form",
                        "ordering": 10,
                        "is_required": True,
                    },
                ),
                (
                    "honeypot",
                    {
                        "type": "honeypot",
                        "label": "",
                        "label_from": "",
                        "region": "form",
                        "ordering": 30,
                        "is_required": "",
                    },
                ),
                (
                    "duration",
                    {
                        "type": "duration",
                        "label": "",
                        "label_from": "from",
                        "region": "form",
                        "ordering": 40,
                        "is_required": "",
                    },
                ),
            ],
        )

    @isolate_apps("testapp")
    def test_form_field_base(self):
        class Field(FormFieldBase):
            pass

        instance = Field()

        with self.assertRaisesRegex(
            NotImplementedError, r"testapp.field needs a get_fields implementation"
        ):
            instance.get_fields()
        with self.assertRaisesRegex(
            NotImplementedError, r"testapp.field needs a get_loaders implementation"
        ):
            instance.get_loaders()

    @isolate_apps("testapp")
    def test_form_field(self):
        class Field(FormField):
            pass

        instance = Field(name="test")

        # Replace get_fields with get_field when deprecation ends.
        with self.assertWarnsRegex(DeprecationWarning, r"self.get_field()"):
            fields = instance.get_fields(form_class=forms.CharField)

        self.assertEqual(set(fields), {"test"})
        self.assertIsInstance(fields["test"], forms.CharField)

        loaders = instance.get_loaders()
        self.assertEqual(len(loaders), 1)

    @isolate_apps("testapp")
    def test_unknown_simple_field_type(self):
        with self.assertRaisesRegex(
            ImproperlyConfigured,
            r"Model <SimpleField_anything: > has unhandled type ''",
        ):
            Anything().get_fields()

        self.assertEqual(Anything.TYPE, "anything")

    def test_all_simpleformfield_types(self):
        cf = ConfiguredForm.objects.create(name="Test", form_type="contact")
        plugins = [
            Text,
            Email,
            URL,
            Date,
            Integer,
            Textarea,
            Checkbox,
            Select,
            Radio,
            SelectMultiple,
            CheckboxSelectMultiple,
        ]
        for index, cls in enumerate(plugins):
            cls.objects.create(
                parent=cf,
                region="form",
                ordering=10 * index,
                label="field",
                name=f"field_{index}",
            )

        # Doesn't crash ;-)
        create_form(
            contents_for_item(cf, plugins=plugins),
            form_kwargs={"auto_id": ""},
        )

    def test_incorrect_type(self):
        cf = ConfiguredForm.objects.create(name="Test", form_type="contact")
        self.assertEqual(
            list(cf.type.validate(cf)),
            [
                Error("Required fields are missing: 'email'."),
                Warning("Expected field 'email' doesn't exist."),
            ],
        )

        Text.objects.create(
            parent=cf,
            region="form",
            ordering=10,
            label="Email",
            name="email",
        )

        self.assertEqual(
            list(cf.type.validate(cf)),
            [
                Error(
                    "The 'type' attribute of the field 'email' doesn't have the expected value 'email'."
                )
            ],
        )

    def test_str(self):
        self.assertEqual(
            str(PlainText(text="1234567890" * 10)),
            "1234567890" * 4,
        )

        self.assertEqual(
            str(Duration(label_from="f", label_until="u")),
            "f - u",
        )
