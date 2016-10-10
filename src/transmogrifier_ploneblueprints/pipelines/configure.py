# -*- coding: utf-8 -*-
"""
This module scans all direct submodules for component registrations in this
package when included for zope.configuration with venusianconfiguration.

"""
from configparser import ParsingError
from configparser import RawConfigParser
from io import StringIO
from venusianconfiguration import configure

import logging
import os
import pkg_resources


# Register pipelines
for resource in pkg_resources.resource_listdir(__package__, ''):
    name, ext = os.path.splitext(resource)

    if ext == '.cfg':
        # Parse to read title and description
        data = pkg_resources.resource_string(__package__, resource)
        config = RawConfigParser()
        try:
            config.readfp(StringIO(data.decode('utf-8')))
        except ParsingError:
            logging.exception('${0:s} has errors:'.format(name))
            continue

        # Register
        configure.transmogrifier.pipeline(
            name=name,
            title=config.get('transmogrifier', 'title'),
            description=config.get('transmogrifier', 'description'),
            configuration=resource
        )
