#!/usr/bin/env python
import os
import sys

import django
from django.conf import settings
from django.test.utils import get_runner

if __name__ == "__main__":
    settings_files = {
        "contrib_sites": "tests.contrib_sites",
        "no_sites": "tests.no_sites",
        "alt_sites": "tests.alt_sites",
    }
    if len(sys.argv) > 1 and sys.argv[1] in settings_files:
        settings_module = settings_files[sys.argv[1]]
    else:
        # Prompt the user to select a settings file
        print("Please select a settings file:")
        for key in settings_files:
            print(f"  {key}")
        settings_module = settings_files[input().strip()]

    os.environ["DJANGO_SETTINGS_MODULE"] = settings_module
    django.setup()
    TestRunner = get_runner(settings)
    test_runner = TestRunner()
    failures = test_runner.run_tests(["tests"])
    sys.exit(bool(failures))
