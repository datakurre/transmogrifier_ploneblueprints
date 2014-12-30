# -*- coding: utf-8 -*-
import doctest
import logging
import os
import unittest

from transmogrifier import Transmogrifier
from transmogrifier_ploneblueprints.testing import \
    PLONEBLUEPRINTS_FUNCTIONAL_TESTING
from zope.testing.loggingsupport import InstalledHandler

from plone.testing import layered


def test_suite():
    suite = unittest.TestSuite()
    my_dir = os.path.dirname(__file__)
    docs = os.path.join('..', '..', '..', 'docs')
    registerConfiguration = PLONEBLUEPRINTS_FUNCTIONAL_TESTING \
        .baseResolutionOrder[1].registerConfiguration
    for filename in os.listdir(os.path.join(my_dir, docs)):
        path = os.path.join(docs, filename)
        globs = {'registerConfiguration': registerConfiguration,
                 'Transmogrifier': Transmogrifier({}),
                 'logger': InstalledHandler('logger', level=logging.DEBUG)}
        flags = doctest.NORMALIZE_WHITESPACE
        suite.addTests([
            layered(doctest.DocFileSuite(path, globs=globs, optionflags=flags),
                    layer=PLONEBLUEPRINTS_FUNCTIONAL_TESTING)
        ])
    return suite
