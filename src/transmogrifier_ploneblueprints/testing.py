# -*- coding:utf-8 -*-
import os
import tempfile
import shutil

from transmogrifier.registry import configuration_registry

from plone.app.testing import PloneSandboxLayer
from plone.app.testing import PLONE_FIXTURE
from plone.app.testing import IntegrationTesting
from plone.app.testing import FunctionalTesting


class PloneBlueprints(PloneSandboxLayer):

    defaultBases = (PLONE_FIXTURE,)

    tempdir = None

    # noinspection PyUnusedLocal
    def setUpZope(self, app, configurationContext):
        import venusianconfiguration
        venusianconfiguration.enable()

        import transmogrifier
        self.loadZCML(package=transmogrifier,
                      name='meta.zcml')
        self.loadZCML(package=transmogrifier,
                      name='configure.zcml')

        import transmogrifier_ploneblueprints
        self.loadZCML(package=transmogrifier_ploneblueprints,
                      name='configure.py')

        # Temp dir for in-test configurations
        self.tempdir = tempfile.mkdtemp('transmogrifierTestConfigs')

    def setUpPloneSite(self, portal):
        portal.portal_workflow.setDefaultChain('simple_publication_workflow')

    # noinspection PyUnusedLocal
    def tearDownZope(self, app):
        shutil.rmtree(self.tempdir)

    def registerConfiguration(self, name, configuration):
        filename = os.path.join(self.tempdir, '{0:s}.cfg'.format(name))
        with open(filename, 'w') as fp:
            fp.write(configuration)
        configuration_registry.registerConfiguration(
            name=name,
            title="Pipeline configuration '{0:s}' from "
                  "'transmogrifier_ploneblueprints.tests'".format(name),
            description='',
            configuration=filename
        )

PLONEBLUEPRINTS_FIXTURE = PloneBlueprints()

PLONEBLUEPRINTS_INTEGRATION_TESTING = IntegrationTesting(
    bases=(PLONEBLUEPRINTS_FIXTURE,),
    name='PloneBlueprints:Integration')

PLONEBLUEPRINTS_FUNCTIONAL_TESTING = FunctionalTesting(
    bases=(PLONEBLUEPRINTS_FIXTURE,),
    name='PloneBlueprints:Functional')
