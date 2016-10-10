# -*- coding: utf-8 -*-
from plone import api
from plone.testing import layered
from transmogrifier.interfaces import ITransmogrifier
from transmogrifier_ploneblueprints.testing import PLONEBLUEPRINTS_FUNCTIONAL_TESTING  # noqa
from zope.testing.loggingsupport import InstalledHandler

import doctest
import logging
import os
import unittest


def test_suite():
    suite = unittest.TestSuite()
    my_dir = os.path.dirname(__file__)
    docs = os.path.join('..', '..', '..', 'docs')
    registerConfiguration = PLONEBLUEPRINTS_FUNCTIONAL_TESTING \
        .baseResolutionOrder[1].registerConfiguration
    for filename in os.listdir(os.path.join(my_dir, docs)):
        path = os.path.join(docs, filename)
        globs = {'registerConfiguration': registerConfiguration,
                 'ITransmogrifier': ITransmogrifier, 'api': api,
                 'logger': InstalledHandler('logger', level=logging.INFO)}
        flags = doctest.NORMALIZE_WHITESPACE | doctest.ELLIPSIS
        suite.addTests([
            layered(doctest.DocFileSuite(path, globs=globs, optionflags=flags),
                    layer=PLONEBLUEPRINTS_FUNCTIONAL_TESTING)
        ])
    return suite
