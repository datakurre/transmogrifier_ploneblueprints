# -*- coding: utf-8 -*-
"""
This module scans all direct submodules for component registrations in this
package when included for zope.configuration with venusianconfiguration.

"""
import importlib
import os

import pkg_resources
from venusianconfiguration import configure
from venusianconfiguration import scan


# Scan modules
for resource in pkg_resources.resource_listdir(__package__, ''):
    name, ext = os.path.splitext(resource)
    if ext == '.py' and name not in ('__init__', 'configure', 'testing'):
        path = '{0:s}.{1:s}'.format(__package__, name)
        scan(importlib.import_module(path))

from transmogrifier_ploneblueprints import pipelines
configure.include(package=pipelines, file='configure.py')
