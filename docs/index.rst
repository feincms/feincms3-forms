==============
feincms3-forms
==============

.. image:: https://github.com/matthiask/feincms3-forms/actions/workflows/tests.yml/badge.svg
    :target: https://github.com/matthiask/feincms3-forms/
    :alt: CI Status

feincms3-forms is an extremely flexible forms builder for the Django admin
interface. It uses `django-content-editor
<https://django-content-editor.readthedocs.io/>`__ to build forms, which
enables:

- Build your own form in the CMS without programmer involvement.
- Reorder, add and remove pre-existing fields.
- Add content (text, images, anything) between form fields.
- Use regions to add additional structure to a form, e.g. to build configurable
  multi-step forms (wizards).
- Add your own form field plugins with all the flexibility and configurability
  you desire.

If you only want to integrate short and simple forms (e.g. a contact form)
you're probably better off using `form_designer
<https://github.com/feincms/form_designer>`__. The feincms3 documentation
contains a `guide showing how to integrate it
<https://feincms3.readthedocs.io/en/latest/guides/apps-form-builder.html>`__.


.. toctree::
   :maxdepth: 2
   :caption: Table of contents

   installation
   reference
   custom-fields
   form-structure
   submissions
   reporting
   development
   changelog
