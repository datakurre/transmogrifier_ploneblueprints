# -*- coding: utf-8 -*-
# from io import BytesIO
# import tarfile

from plone import api
from venusianconfiguration import configure

from transmogrifier.blueprints import ConditionalBlueprint


@configure.transmogrifier.blueprint.component(name='plone.genericsetup.export')
class GenericSetupSource(ConditionalBlueprint):
    def __iter__(self):
        for item in self.previous:
            yield item

        # prefix = self.options.get('prefix', '')

        steps = self.options.get('steps').split() or [
            # 'action-icons',
            'actions',
            # 'analytics',
            # 'archetypetool',
            # 'atcttool',
            # 'browserlayer',
            # 'caching_policy_mgr',
            # 'catalog',
            # 'componentregistry',
            # 'content',
            # 'content_type_registry',
            'contentrules',
            # 'controlpanel',
            # 'cookieauth',
            # 'cssregistry',
            # 'difftool',
            # 'factorytool',
            # 'indexing',
            # 'jsregistry'
            # 'kssregistry',
            # 'kupu-setup',
            # 'languagetool',
            # 'ldap-settings-export',
            # 'ldapmultiplugins',
            # 'ldapuserfolder',
            # 'mailhost',
            # 'memberdata-properties',
            # 'plone.app.registry',
            # 'portal_placeful_workflow',
            'portlets',
            'properties',
            # 'propertiestool',
            # 'reference_catalog',
            # 'repositorytool',
            # 'rolemap',
            # 'sharing',
            # 'skins',
            # 'solr',
            # 'step_registries',
            # 'tinymce_settings',
            # 'toolset',
            # 'typeinfo',
            # 'uid_catalog',
            'viewlets',
            'workflows',
        ]

        portal_setup = api.portal.get_tool('portal_setup')

        for step in steps:
            # fb = BytesIO(portal_setup.runExportStep(step)['tarball'])
            # tar = tarfile.open(fileobj=fb, mode='r:gz')

            data = {
                '_type': 'plone.genericsetup.tarball',
                '_step': step,
                '_tarball': portal_setup.runExportStep(step)['tarball']
            }

            if self.condition(data):
                yield data


def import_tarball(portal_setup, item):
    tarball = item.get('tarball')
    portal_setup.runAllImportStepsFromProfile(None, True, archive=tarball)


@configure.transmogrifier.blueprint.component(name='plone.genericsetup.import')
class GenericSetupConstructor(ConditionalBlueprint):

    def __iter__(self):
        portal_setup = api.portal.get_tool('portal_setup')
        for item in self.previous:
            import pdb; pdb.set_trace()
            if self.condition(item) and '_tarball' in item:
                import pdb; pdb.set_trace()
                import_tarball(portal_setup, item)
            yield item
