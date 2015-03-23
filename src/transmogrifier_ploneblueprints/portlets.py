# -*- coding: utf-8 -*-
from Products.GenericSetup.utils import PrettyDocument
from io import BytesIO
from plone import api
from plone.app.portlets.exportimport.interfaces import IPortletAssignmentExportImportHandler  # noqa
from plone.app.portlets.interfaces import IPortletTypeInterface
from plone.portlets.constants import CONTEXT_CATEGORY
from plone.portlets.interfaces import IPortletAssignmentMapping
from plone.portlets.interfaces import IPortletAssignmentSettings
from plone.portlets.interfaces import IPortletManager
from transmogrifier.blueprints import ConditionalBlueprint
from venusianconfiguration import configure
from zope.component import getUtilitiesFor
from zope.component import queryMultiAdapter
from zope.interface import providedBy
import tarfile

import logging
logger = logging.getLogger('transmogrifier')


def extract_mapping(doc, node, manager_name, category, key, mapping):
    portlets_schemata = dict([
        (iface, name) for name, iface
        in getUtilitiesFor(IPortletTypeInterface)
    ])

    for name, assignment in mapping.items():
        type_ = None
        schema = None
        for schema in providedBy(assignment).flattened():
            type_ = portlets_schemata.get(schema, None)
            if type_ is not None:
                break

        if type_ is not None:
            child = doc.createElement('assignment')
            child.setAttribute('manager', manager_name)
            child.setAttribute('category', category)
            child.setAttribute('key', key)
            child.setAttribute('type', type_)
            child.setAttribute('name', name)

            assignment = assignment.__of__(mapping)

            settings = IPortletAssignmentSettings(assignment)
            visible = settings.get('visible', True)
            child.setAttribute('visible', repr(visible))

            handler = IPortletAssignmentExportImportHandler(assignment)
            # noinspection PyArgumentList
            handler.export_assignment(schema, doc, child)
            node.appendChild(child)


def patch_portlets_xml(xml, prefix=None):
    portal = '/'.join(api.portal.get().getPhysicalPath())
    if prefix is not None and prefix.startswith(portal):
        xml = xml.replace('>{0:s}/'.format(prefix[len(portal):]), '>/')

    # This must be a bug in p.a.portlets where it exports assignments, which it
    # cannot import, empty tag cannot be interpreted into an integer
    xml = xml.replace('<property name="limit"/>',
                      '<property name="limit">0</property>')

    return xml


def get_portlet_assignment_xml(context, prefix):
    doc = PrettyDocument()
    node = doc.createElement('portlets')
    for manager_name, manager in getUtilitiesFor(IPortletManager):
        mapping = queryMultiAdapter((context, manager),
                                    IPortletAssignmentMapping)
        if mapping is None:
            continue

        mapping = mapping.__of__(context)

        key = '/'.join(context.getPhysicalPath())
        if key.startswith(prefix):
            key = key[len(prefix):]
        key = key or '/'

        extract_mapping(doc, node, manager_name, CONTEXT_CATEGORY,
                        key, mapping)

    doc.appendChild(node)
    xml = patch_portlets_xml(doc.toprettyxml(' '), prefix)
    doc.unlink()
    return xml


@configure.transmogrifier.blueprint.component(name='plone.portlets.get')
class GetPortlets(ConditionalBlueprint):
    def __iter__(self):
        key = self.options.get('key', '_portlets')
        prefix = self.options.get('prefix', '')  # prefix to remove
        for item in self.previous:
            if self.condition(item):
                if '_object' in item.keys():
                    ob = item['_object']
                    item[key] = get_portlet_assignment_xml(ob, prefix) or None
            yield item


def get_tarball(files):
    fb = BytesIO()
    tar = tarfile.open(fileobj=fb, mode='w:gz')

    for filename, filedata in files.items():
        info = tarfile.TarInfo(filename)
        info.size = len(filedata)
        tar.addfile(info, BytesIO(filedata))

    tar.close()
    return fb.getvalue()


def import_portlets(portal_setup, portlets_xml):
    tarball = get_tarball({'portlets.xml': portlets_xml})
    try:
        portal_setup.runAllImportStepsFromProfile(
            None, purge_old=False, archive=tarball)
    except Exception as e:
        logger.warn(portlets_xml)
        logger.warn('Failed to assign portlets because of %s' % e)


@configure.transmogrifier.blueprint.component(name='plone.portlets.set')
class SetPortlets(ConditionalBlueprint):
    def __iter__(self):
        key = self.options.get('key', '_portlets')
        portal_setup = api.portal.get_tool('portal_setup')

        for item in self.previous:
            if self.condition(item):
                if key in item.keys():
                    portlets_xml = patch_portlets_xml(item[key])
                    import_portlets(portal_setup, portlets_xml)
            yield item
