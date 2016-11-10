# -*- coding: utf-8 -*-
from io import BytesIO
from plone import api
from plone.app.portlets.exportimport.interfaces import IPortletAssignmentExportImportHandler  # noqa
from plone.app.portlets.interfaces import IPortletTypeInterface
from plone.portlets.constants import CONTEXT_CATEGORY
from plone.portlets.interfaces import IPortletAssignmentMapping
from plone.portlets.interfaces import IPortletAssignmentSettings
from plone.portlets.interfaces import IPortletManager
from Products.GenericSetup.utils import PrettyDocument
from transmogrifier.blueprints import ConditionalBlueprint
from transmogrifier_ploneblueprints.utils import resolve_object
from transmogrifier_ploneblueprints.utils import traverse
from venusianconfiguration import configure
from zope.component import getUtilitiesFor
from zope.component import queryMultiAdapter
from zope.interface import providedBy

import logging
import tarfile


try:
    # Fix error where portlet assignment was missing required value
    import plone.portlet.collection.collection
    plone.portlet.collection.collection.Assignment.exclude_context = True
except ImportError:
    pass


logger = logging.getLogger('transmogrifier')


# noinspection PyArgumentList
def extract_mapping(manager_name, category, key, mapping):
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
            child = PrettyDocument().createElement('assignment')
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
            handler.export_assignment(schema, PrettyDocument(), child)

            yield child


def get_portlet_assignment_xml(context, prefix):
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

        for child in extract_mapping(
                manager_name, CONTEXT_CATEGORY, key, mapping):
            doc = PrettyDocument()
            node = doc.createElement('portlets')
            node.appendChild(child)
            doc.appendChild(node)
            xml = patch_get_portlets_xml(doc.toprettyxml(' '), prefix)
            doc.unlink()

            yield xml


def patch_get_portlets_xml(xml, prefix=None):
    portal = api.portal.get()
    portal_path = '/'.join(portal.getPhysicalPath())

    if prefix is not None and prefix.startswith(portal_path):
        xml = xml.replace('>{0:s}/'.format(prefix[len(portal_path):]), '>/')

    # This must be a bug in p.a.portlets where it exports assignments, which it
    # cannot import, empty tag cannot be interpreted into an integer
    xml = xml.replace('<property name="limit"/>',
                      '<property name="limit">0</property>')

    return xml


def patch_set_portlets_xml(xml, prefix=None):
    portal = api.portal.get()
    portal_path = '/'.join(portal.getPhysicalPath())
    if prefix:
        try:
            prefix_target = traverse(portal, prefix)
            prefix = '/'.join(prefix_target.getPhysicalPath())
        except (AttributeError, KeyError):
            prefix = None

    if prefix is not None and prefix.startswith(portal_path):
        xml = xml.replace(
            ' key="/', ' key="' + prefix[len(portal_path):] + '/')

    # This must be a bug in p.a.portlets where it exports assignments, which it
    # cannot import, empty tag cannot be interpreted into an integer
    xml = xml.replace('<property name="limit"/>',
                      '<property name="limit">0</property>')

    return xml


@configure.transmogrifier.blueprint.component(name='plone.portlets.get')
class GetPortlets(ConditionalBlueprint):
    def __iter__(self):
        context = self.transmogrifier.context
        key = self.options.get('key', '_portlets')
        prefix = self.options.get('prefix', '')  # prefix to remove
        for item in self.previous:
            if self.condition(item):
                obj = resolve_object(context, item)
                item[key] = tuple(get_portlet_assignment_xml(obj, prefix))
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
        prefix = self.options.get('prefix') or None

        for item in self.previous:
            if self.condition(item):
                for portlets_xml in item.get(key):
                    import_portlets(portal_setup, patch_set_portlets_xml(
                        portlets_xml, prefix=prefix))
            yield item
