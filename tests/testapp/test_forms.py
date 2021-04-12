from django import test
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

from .models import ConfiguredForm, Honeypot, PlainText, Select, Text


# from django.test.utils import override_settings
# from django.utils.functional import lazy


class FormsTest(test.TestCase):
    def test_stuff(self):
        cf = ConfiguredForm.objects.create(name="Test", form="contact")
        Text.objects.create(
            parent=cf,
            region="form",
            ordering=10,
            label="Full name",
            key="full_name",
        )
        PlainText.objects.create(
            parent=cf,
            region="form",
            ordering=20,
            text="Something",
        )

        response = self.client.get("/")
        prefix = response.context["form"].prefix
        self.assertContains(
            response,
            f'<input type="text" name="{prefix}-full_name" required>',
            html=True,
        )

    def test_admin(self):
        user = User.objects.create_superuser("admin", "admin@example.com", "password")
        self.client.force_login(user)

        cf = ConfiguredForm.objects.create(name="Test", form="contact")
        response = self.client.get(f"/admin/testapp/configuredform/{cf.id}/change/")

        self.assertContains(response, "&quot;testapp_simplefield_set&quot;")
        self.assertContains(response, "&quot;testapp_simplefield_set-2&quot;")
        self.assertContains(response, "&quot;testapp_simplefield_set-8&quot;")
        # print(response, response.content.decode("utf-8"))

        self.assertContains(response, " has been validated.")
        self.assertContains(response, "&quot;email&quot; key is missing")

    def test_form_without_items(self):
        ConfiguredForm.objects.create(name="Test", form="contact")
        response = self.client.get("/")
        prefix = response.context["form"].prefix
        self.assertEqual(prefix, None)

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
            "key": "key",
            "type": "select",
        }

        item = Select(choices="a\nb", default_value="", **kw)
        item.full_clean()  # Validates just fine
        self.assertEqual(
            item.get_fields()["key"].choices,
            [("", "----------"), ("a", "a"), ("b", "b")],
        )

        item.default_value = "b"
        item.full_clean()  # Validates just fine
        self.assertEqual(
            item.get_fields()["key"].choices,
            [("a", "a"), ("b", "b")],
        )

        with self.assertRaises(ValidationError) as cm:
            item.default_value = "c"
            item.full_clean()

        self.assertEqual(
            cm.exception.error_dict["default_value"][0].message,
            'The specified default value "c" isn\'t part of' " the available choices.",
        )

        kw["type"] = "radio"

        item = Select(choices="A\nB is fun", default_value="", **kw)
        item.full_clean()  # Validates just fine

        initial = {}
        self.assertEqual(
            item.get_fields(initial=initial)["key"].choices,
            [("a", "A"), ("b-is-fun", "B is fun")],
        )
        self.assertNotIn("key", initial)

        item.default_value = "B is fun"
        item.get_fields(initial=initial)
        self.assertEqual(initial["key"], "b-is-fun")

        item = Select(
            choices="KEY VALUE | pretty label\n OTHER VALUE | other pretty label \n\n",
            default_value="",
            **kw,
        )
        item.full_clean()  # Validates just fine
        self.assertEqual(
            item.get_fields()["key"].choices,
            [
                ("KEY VALUE", "pretty label"),
                ("OTHER VALUE", "other pretty label"),
            ],
        )

    def test_other_fields(self):
        ConfiguredForm.objects.create(name="Test", form="other-fields")

        response = self.client.get("/")
        self.assertEqual(response.context["form"].prefix, None)
        self.assertContains(
            response,
            '<input type="email" name="email" required>',
            html=True,
        )

    def test_honeypot(self):
        cf = ConfiguredForm.objects.create(name="Test", form="contact")
        Honeypot.objects.create(
            parent=cf,
            region="form",
            ordering=10,
        )

        response = self.client.get("/")
        prefix = response.context["form"].prefix
        self.assertContains(
            response,
            f'<input type="hidden" name="{prefix}-honeypot">',
            html=True,
        )

        response = self.client.post("/", {f"{prefix}-honeypot": "anything"})
        self.assertContains(response, "Invalid honeypot value")
        # print(response, response.content.decode("utf-8"))
