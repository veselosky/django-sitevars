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

## General Usage

### In Templates

In templates, load the `sitevars` library to use the included template tag.

```html
{% load sitevars %} Hello, {% sitevar "name" default="world" %}!
```

Or, if you are using the `sitevars.context_processors.inject_sitevars` context processor,
the variable will already be in the template context, and the tag is not needed.
```html
Hello, {{ name|default:"world" }}!
```

NOTE: It's strongly advised to use the `django.template.context_processors.request`
context processor to ensure `sitevars` can look up the current site.

### In Python

In your views, you can access site variables via the `vars` accessor on the site object.
To get the current site object regardless of what SITE_MODEL you're using, the sitevars
AppConfig provides a `get_site_for_request` method (even if you don't have a site model,
sitevars provides one). See the example below.

Use the `site.vars.get_value` method to retrieve the value by name. The signature for
`get_value` is:

```python
def get_value(self, name: str, default: object = "", asa: Callable = str):
```

Although the values are always stored as strings in the database, you can also ask
`get_value` to transform the string value returned from the database by passing a
function in the `asa` argument. Here are some examples for various types:

- **Integer:** Use `num = site.vars.get_value("name", default=10, asa=int)`. Remember an
  empty value cannot be converted to an `int` so you should always pass a default. Will
  raise `ValueError` if the string cannot be converted to an `int`.
- **Float:** `num = site.vars.get_value("name", default=1.0, asa=float)`. As with
  integers, it is wise to pass a default, and it will raise `ValueError` if the
  conversion fails.
- **Boolean:** `tf = site.vars.get_value("name", asa=bool)`. We special-case Boolean
  values, so if the database value is "", "0", or "false" (case insensitive), or not
  set, it returns `False`. Any other stored value returns `True`. If you want `True` for
  unset values you can pass `default=True`.
- **JSON:** For complex types, store serialized JSON and use
  `num = site.vars.get_value("name", default={}, asa=json.loads)`. If the field does not
  contain a valid JSON string this will raise JSONDecodeError. If the type returned from
  `loads` is not the same type as your default, this will raise `TypeError`. If you
  don't provide a default and the value is not set, this will also raise
  `JSONDecodeError` (because it will end up calling `loads("")`).

```python
import json
from django.apps import apps
from django.contrib.sites.shortcuts import get_current_site

sitevars = apps.get_app_config("sitevars")


def my_view(request):
    site = sitevars.get_site_for_request(request)
    # Returns the string if set, or "" if not set
    x = site.vars.get_value("analytics_id")
    # Returns the string if set, or "Ignore" if not set
    x = site.vars.get_value("abort_retry_ignore", "Ignore")
    # Returns the number of pages as an integer. Raises ValueError if the
    # value is not a number.
    num_items = site.vars.get_value("paginate_by", default=10, asa=int)
    # Booleans may store "false", "0", or "" as false. Anything else is true.
    is_good = site.vars.get_value("is_good", default=False, asa=bool)
    # Parses the value as JSON and returns the result. If you pass default as a
    # string, it will be passed to the asa function for transformation. Here if
    # value is not set, it will return an empty dict.
    data = site.vars.get_value("json_data", "{}", json.loads)
    # If the value is not valid JSON ("" is not!), it will raise JSONDecodeError.
    # This raises JSONDecodeError if not set.
    data = site.vars.get_value("json_data", json.loads)
    # If you pass a non-string as default, it will check that the decoded value
    # is of the same type, or raise a ValueError.
    SiteVar.objects.create(
        site=site, name="json_data", value='{"key": "value"}'
    )
    # Raises ValueError. Expected list, but value decoded to dict.
    data = site.vars.get_value("json_data", [], json.loads)
    ...
```

The manager also provides `get_multiple_values` which returns multiple values in a
single query. It works similarly, but takes a list of names, defaults are passed as a
`dict`, and `asa` may also be a dict. If you pass no names, returns ALL values for the
site.

```python
    def get_multiple_values(
        self,
        names: T.Optional[T.List[str]] = None,
        *,
        defaults: T.Optional[T.Mapping] = None,
        asa: T.Union[T.Callable, T.Mapping] = str,
    ) -> T.Dict[str, object]:
```

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

# In my_sites_app/utils.py
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

However, you can also get the current site object as shown above, and that will also
work.

## Building reusable apps with swappable site model

`sitevars` exposes some utilities to make it easier to build reusable apps that support
a swappable site model. To use them, first fetch the AppConfig:

```python
from django.apps import apps
sitevars = apps.get_app_config("sitevars")
```

The following properties and methods are available on the resulting object.

- `site_model`: Property that holds the Django name of the site model, e.g.
  "sites.Site".
- `Site`: Property that holds the model class itself.
- `get_site_for_request(request)`: Given a request, returns the model instance
  representing the current site (using whatver site framework has been configured).
- `get_site_id_for_request(request)`: Given a request, returns the primary key of the
  current site. This is useful if you only need to filter a queryset on `site_id` but
  don't otherwise need the site object. Saves some memory and possibly a database query.

Note that Django does not directly support a swappable site model, so when you generate
migrations, your migration file will have hard dependencies and literals for its site
foreign keys. Edit the migration to import the `sitevars` AppConfig as above. In the
`Migration.dependencies` replace the listed sites migration with
`migrations.swappable_model(sitevars.site_model)` and change any site foreign keys to
use `sitevars.site_model`.

```python
import django.db.models.deletion
from django.apps import apps
from django.db import migrations, models

sitevars = apps.get_app_config("sitevars")

class Migration(migrations.Migration):

  dependencies = [
    # ("sites", "0002_alter_domain_unique"),  # If django.contrib.sites
    migrations.swappable_dependency(sitevars.site_model),
  ]
  operations = [
    migrations.CreateModel(
      name="MyModel",
      fields=[
        (
          "id",
          models.BigAutoField(
              auto_created=True,
              primary_key=True,
              serialize=False,
              verbose_name="ID",
          ),
        ),
        (
          "site",
          models.ForeignKey(
              on_delete=django.db.models.deletion.CASCADE,
              related_name="something",
              # to="sites.Site",  # Django inserts this
              to=config.site_model,  # Replace with this
              verbose_name="site",
          ),
        ),
      ]
    )
  ]
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
