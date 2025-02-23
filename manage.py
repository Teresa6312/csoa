#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys


def main():
    """Run administrative tasks."""

    settings_local = 'csoa/settings_local.py'
    settings_test = 'csoa/settings_test.py'
    try:
        if os.path.exists(settings_local):
            os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'csoa.settings_local')
        elif os.path.exists(settings_test):
            os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'csoa.settings_test')
        else:
            os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'csoa.settings_production')
    except Exception as e:
        print(e)

    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
