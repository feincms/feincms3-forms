from django import test
from django.test.utils import override_settings
from django.utils.functional import lazy

from feincms3_meta.utils import MetaTags, meta_tags

from .models import Model


class MetaTest(test.TestCase):
    def test_basic_meta_tags(self):
        request = test.RequestFactory().get("/")
        self.assertEqual(
            str(meta_tags(request=request)),
            """\
<meta property="og:type" content="website">
  <meta property="og:url" content="http://testserver/">""",
        )

        lazy_url = lazy(lambda: "/lazy/", str)()
        self.assertEqual(
            str(meta_tags(url=lazy_url, request=request)),
            """\
<meta property="og:type" content="website">
  <meta property="og:url" content="http://testserver/lazy/">""",
        )

        self.assertEqual(
            str(meta_tags(request=request, defaults={"title": "stuff"}, title=None)),
            """\
<meta property="og:type" content="website">
  <meta property="og:url" content="http://testserver/">""",
        )

    def test_model(self):
        m = Model()
        request = test.RequestFactory().get("/stuff/")
        self.assertEqual(
            str(meta_tags([m], request=request)),
            """\
<meta property="og:type" content="website">
  <meta property="og:url" content="http://testserver/stuff/">""",
        )

        m.meta_canonical = "/bla/"
        self.assertEqual(
            str(meta_tags([m], request=request)),
            """\
<meta property="og:type" content="website">
  <meta property="og:url" content="http://testserver/bla/">
  <link rel="canonical" href="http://testserver/bla/">""",
        )

        # meta_title not set, falling back to title
        m.title = "test"
        self.assertEqual(
            str(meta_tags([m], request=request)),
            """\
<meta property="og:title" content="test">
  <meta property="og:type" content="website">
  <meta property="og:url" content="http://testserver/bla/">
  <link rel="canonical" href="http://testserver/bla/">""",
        )

        m = Model()
        m.meta_title = "title-test"
        # Generate both name="description" and property="og:description"
        m.meta_description = "description-test"
        self.assertEqual(
            str(meta_tags([m], request=request)),
            """\
<meta property="og:description" content="description-test">
  <meta property="og:title" content="title-test">
  <meta property="og:type" content="website">
  <meta property="og:url" content="http://testserver/stuff/">
  <meta name="description" content="description-test">""",
        )

        # print(str(meta_tags([m], request=request)))

    def test_unknown_attribute_not_rendered(self):
        request = test.RequestFactory().get("/")
        self.assertEqual(
            str(meta_tags([], request=request, unknown="Stuff")),
            """\
<meta property="og:type" content="website">
  <meta property="og:url" content="http://testserver/">""",
        )

    @override_settings(
        META_TAGS={
            "site_name": "site",
            "title": "t",
            "description": "desc",
            "image": "/logo.png",
            "robots": "noindex",
        }
    )
    def test_setting(self):
        request = test.RequestFactory().get("/")
        self.assertEqual(
            str(meta_tags([], request=request, unknown="Stuff")),
            """\
<meta property="og:description" content="desc">
  <meta property="og:image" content="http://testserver/logo.png">
  <meta property="og:site_name" content="site">
  <meta property="og:title" content="t">
  <meta property="og:type" content="website">
  <meta property="og:url" content="http://testserver/">
  <meta name="description" content="desc">
  <meta name="robots" content="noindex">""",
        )

    @override_settings(META_TAGS=None)
    def test_setting_none(self):
        request = test.RequestFactory().get("/")
        self.assertEqual(
            str(meta_tags([], request=request, unknown="Stuff")),
            """\
<meta property="og:type" content="website">
  <meta property="og:url" content="http://testserver/">""",
        )

    def test_as_dict(self):
        mt = MetaTags()
        self.assertEqual(str(mt), "")

        mt["url"] = "test"
        self.assertEqual(str(mt), '<meta property="og:url" content="test">')
