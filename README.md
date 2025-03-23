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

Then, configure and use it according to the usage scenarios below.

## Using with `django.contrib.sites`

If you have `django.contrib.sites` in your installed apps, SiteVars will be associated
with the `sites.Site` model.

Add `sitevars` to `INSTALLED_APPS` in your Django settings. Optionally, you can
configure the provided context processor to add your site variables into every template
context.

Note: If you use the `django.contrib.sites` app, `sitevars` must be added to
INSTALLED_APPS **AFTER** `django.contrib.sites` in order to augment the sites admin.

```python
INSTALLED_APPS = [
    ...
    'django.contrib.sites',  # must come first
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
                "django.template.context_processors.request",  # strongly advised
                "sitevars.context_processors.inject_sitevars",  # optional, but useful
            ]
        },
    }
]
# highly recommended to add the current site middleware
# MIDDLEWARE.append("django.contrib.sites.middleware.CurrentSiteMiddleware")
```

In your views, you can access site variables via the accessor on the site object. Use
the `get_value` method to retrieve the value by name. You can also ask `get_value` to
transform the string value returned from the database by passing a function in the `asa`
argument.

```python
import json
from django.contrib.sites.shortcuts import get_current_site

def my_view(request):
  site = get_current_site(request)
  name = site.vars.get_value("name", default="world")
  # Note that default must be a string, because it will be passed to your asa function!
  number = site.vars.get_value("number", default="0", asa=int)
  options_dict = site.vars.get_value("options", default="{}", asa=json.loads)
  ...
```

## Using with an alternate Site model

If you use a Site model other than the `django.contrib.sites` model, you will need to
add some settings to tell `sitevars` what model to target in its foreign keys, and how
to get the correct Site for the current request.

The `SITE_MODEL` setting should be a string identifying the model in the usual Django
fashion, "appname.Model".

WARNING: As with a custom AUTH_USER_MODEL, if you're going to use a custom SITE_MODEL in
your project, be sure to set SITE_MODEL **BEFORE** running initial migrations for the
`sitevars` app. Otherwise, you will have a mess to untangle.

NOTE: Apps that ship with Django do not support custom SITE_MODEL, so don't try to use a
custom SITE_MODEL with `django.contrib.flatpages` or `django.contrib.redirects`, or any
third party app that depends on the Django sites framework.

### Determining the current site

The recommended way to make `sitevars` aware of the current site is to use a Current
Site Middleware that sets `request.site` as
`django.contrib.sites.middleware.CurrentSiteMiddleware` does. `sitevars` will always use
this when available.

Without a middleware, you will need to tell `sitevars` how to determine the current
site.

If the site model has a class method that will return the correct site given the
request, set `CURRENT_SITE_METHOD="method_name"`.

If there's no such method on the class, then you must provide an importable function
that takes a request and returns a site object:
`CURRENT_SITE_FUNCTION="myapp.utils.get_current_site"`.

In the absence of a CURRENT_SITE_METHOD or CURRENT_SITE_FUNCTION, `sitevars` will fall
back to trying `Site.objects.get_current(request)` (which is how it works for Django's
sites framework.)

For example, the following settings should work for a Wagtail project.

```python
SITE_MODEL = "wagtailcore.Site"
CURRENT_SITE_METHOD = "find_for_request"
# sitevars will import wagtailcore.Site and call Site.find_for_request(request)
```

For a home-grown custom site model, something like this should work:

```python
# In settings.py
SITE_MODEL = "my_sites_app.Site"
CURRENT_SITE_FUNCTION = "my_sites_app.utils.site_for_request"

# In my_sites_app.utils.py
def site_for_request(request):
    # Your own matching logic here
    return Site.objects.matching_domain(request.get_host())
```

## Using without a Site model

If you don't use a sites framework because your project only serves one site, no
worries! `django-sitevars` will work fine for a single site. In this case, `sitevars`
creates a placeholder site object for its foreign key, but you don't need to know about
it. Just call `SiteVar.objects.get_value("name")` and `sitevars` will do the right
thing.

## Using in templates

In templates, load the `sitevars` library to use the included template tag.

```html
{% load sitevars %} Hello, {% sitevar "name" default="world" %}!
```

Or, if you are using the `sitevars.contet_processors.inject_sitevars` context processor,
the variable will already be in the template context.

```html
{% load sitevars %} Hello, {{ name|default:"world" }}!
```

NOTE: It's strongly advised to use the `django.template.context_processors.request`
context processor to ensure `sitevars` can look up the current site.

## Disabling the Cache

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
