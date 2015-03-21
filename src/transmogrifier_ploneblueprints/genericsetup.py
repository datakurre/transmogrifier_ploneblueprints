# -*- coding: utf-8 -*-
from io import BytesIO
import tarfile
from lxml import etree

from plone import api
from venusianconfiguration import configure

from transmogrifier.blueprints import ConditionalBlueprint


@configure.transmogrifier.blueprint.component(name='plone.genericsetup.export')
class GenericSetupSource(ConditionalBlueprint):
    def __iter__(self):
        for item in self.previous:
            yield item

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

            data = {
                '_type': 'plone.genericsetup.tarball',
                '_step': step,
                '_tarball': portal_setup.runExportStep(step)['tarball']
            }

            if self.condition(data):
                yield data


# noinspection PyUnresolvedReferences
def behead(tarball):
    fb = BytesIO(tarball)
    tar = tarfile.open(fileobj=fb, mode='r:gz')

    fb2 = BytesIO()
    tar2 = tarfile.open(fileobj=fb2, mode='w:gz')

    for info in tar:
        file_ = tar.extractfile(info)
        root = etree.fromstring(file_.read())

        # Magic happens

        tar2.addfile(info, BytesIO(etree.tostring(root)))
    tar2.close()

    return fb2.getvalue()


@configure.transmogrifier.blueprint.component(name='plone.genericsetup.behead')
class GenericSetupBehead(ConditionalBlueprint):

    def __iter__(self):
        prefix = self.options.get('prefix')
        for item in self.previous:
            if self.condition(item) and '_tarball' in item and prefix:
                item['_tarball'] = behead(item['_tarball'])
            yield item


def import_tarball(portal_setup, item):
    tarball = item.get('tarball')
    portal_setup.runAllImportStepsFromProfile(None, True, archive=tarball)


@configure.transmogrifier.blueprint.component(name='plone.genericsetup.import')
class GenericSetupConstructor(ConditionalBlueprint):

    def __iter__(self):
        portal_setup = api.portal.get_tool('portal_setup')
        for item in self.previous:
            if self.condition(item) and '_tarball' in item:
                import_tarball(portal_setup, item)
            yield item
