# Django SiteVars

A Django app for managing site-wide variables. Ever have a need to store some small
value related to a site? An analytics ID perhaps, or a copyright statement. SiteVars
provides a simple and efficient way to store those values in your database and edit them
through the Django admin interface.

## Installation

To install the package, use pip:

```sh
pip install django-sitevars
```

Add sitevars to INSTALLED_APPS in your Django settings. Optionally, you can configure
the provided context processor to add your site variables into every template context.

Note: If you use the `django.contrib.sites` app, `sitevars` must be added to
INSTALLED_APPS **AFTER** `django.contrib.sites` in order to augment the sites admin.

```python
INSTALLED_APPS = [
    ...
    'django.contrib.sites',  # optional, but if present, must come first
    'sitevars',  # Must come after contrib.sites for admin to work
    ...
]
TEMPLATES=[
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",  # required
                "sitevars.context_processors.inject_sitevars",  # optional
            ]
        },
    }
]
```

If you use a sites framework other than `django.contrib.sites` (e.g. Wagtail), you can
associate the site variables with your framework's sites by setting SITE_MODEL in your
`settings.py`:

```python
SITE_MODEL = "wagtail.site"
```

WARNING: As with a custom AUTH_USER_MODEL, if you're going to use a custom SITE_MODEL in
your project, be sure to set SITE_MODEL **BEFORE** running initial migrations for the
`sitevars` app. Otherwise, you will have a mess to untangle.

NOTE: Apps that ship with Django do not support custom SITE_MODEL, so don't try to use a
custom SITE_MODEL with `django.contrib.flatpages` or `django.contrib.redirects`, or any
third party app that depends on the Django sites framework.

If you don't use a sites framework because your project only serves one site, no
worries! `django-sitevars` will work fine for a single site.

## Usage

In templates, load the `sitevars` library to use the included template tag.

```html
{% load sitevars %} Hello, {% sitevar "name" default="world" %}!
```

Or, if you are using the `inject_sitevars` context processor, the variable will already
be in the template context.

```html
{% load sitevars %} Hello, {{ name|default:"world" }}!
```

In your views, you can access site variables via the accessor on the site object. Use
the `get_value` method to retrieve the value by name.

```python
from django.contrib.sites.shortcuts import get_current_site

def my_view(request):
  site = get_current_site(request)
  name = site.vars.get_value("name", default="world")
  ...
```

To reduce load on the database, `sitevars` maintains a cache of all variables per site
(using the default cache configured in your Django project). If you prefer not to use
the cache for some reason, you can disable it in your settings file.

```python
SITEVARS_USE_CACHE = False
```

## Development

I recommend using [Astral's uv](https://docs.astral.sh/uv/) to manage your local
development environment. This project uses [pre-commit](https://pre-commit.com/). After
installing uv, clone this repository, then:

```bash
uv sync
uv run pre-commit install
```

Tests are run using a test script and/or tox.

```bash
uv run python -Wall runtests.py  # unit tests
tox run  # full test matrix
tox p  # Run full test matrix in parallel (much faster)
```

Note that the `tests` directory contains multiple settings files for testing the various
supported project configurations. The test script will ask which settings file to use,
or you can supply one on the command line.

`uv run python -Wall runtests.py <contrib_sites | alt_sites | no_sites>`

If you need to generate migrations for the FakeSite model in the tests app for some
reason, be sure to use the `alt_sites` settings.

`DJANGO_SETTINGS_MODULE=tests.alt_sites uv run python ./manage.py makemigrations`

## License

This project is licensed under the Apache License 2.0. See the LICENSE file for details.
