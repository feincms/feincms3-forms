from django import test
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

from .models import ConfiguredForm, PlainText, Select, Text


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
        }

        Select(choices="a\nb", default_value="b", **kw).full_clean()
        Select(choices="a\nb", default_value="", **kw).full_clean()

        with self.assertRaises(ValidationError) as cm:
            Select(choices="a\nb", default_value="c", **kw).full_clean()

        self.assertEqual(
            cm.exception.error_dict["default_value"][0].message,
            'The specified default value "c" isn\'t part of' " the available choices.",
        )
