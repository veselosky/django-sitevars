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

Add sitevars to your INSTALLED_APPS in your Django settings. Optionally, you can
configure the provided context processor to add your site variables into every template
context.

```python
INSTALLED_APPS = [
    ...
    'django.contrib.sites',  # required
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
uv venv
uv pip install -e .[dev]
pre-commit install
```

Tests are run using pytest and tox.

```bash
pytest test_project  # unit tests
tox run  # full test matrix
```

## License

This project is licensed under the Apache License 2.0. See the LICENSE file for details.
