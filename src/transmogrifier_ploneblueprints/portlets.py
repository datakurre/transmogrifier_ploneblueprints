# -*- coding: utf-8 -*-
from Products.GenericSetup.utils import PrettyDocument
from plone.app.portlets.exportimport.interfaces import \
    IPortletAssignmentExportImportHandler
from plone.app.portlets.interfaces import IPortletTypeInterface
from plone.portlets.constants import CONTEXT_CATEGORY
from plone.portlets.interfaces import IPortletAssignmentSettings
from plone.portlets.interfaces import IPortletManager
from plone.portlets.interfaces import IPortletAssignmentMapping
from venusianconfiguration import configure
from zope.component import getUtilitiesFor
from zope.component import queryMultiAdapter
from zope.interface import providedBy

from transmogrifier.blueprints import ConditionalBlueprint


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


def get_portlet_assignment_xml(context):
    doc = PrettyDocument()
    node = doc.createElement('portlets')
    for manager_name, manager in getUtilitiesFor(IPortletManager):
        mapping = queryMultiAdapter((context, manager),
                                    IPortletAssignmentMapping)
        if mapping is None:
            continue

        mapping = mapping.__of__(context)
        extract_mapping(
            doc, node, manager_name, CONTEXT_CATEGORY,
            '/'.join(context.getPhysicalPath()), mapping
        )
    doc.appendChild(node)
    xml = doc.toprettyxml(' ')
    doc.unlink()
    print xml
    return xml


@configure.transmogrifier.blueprint.component(name='plone.portlets.get')
class GetPortlets(ConditionalBlueprint):
    def __iter__(self):
        key = self.options.get('key', '_portlets')
        for item in self.previous:
            if self.condition(item):
                if '_object' in item.keys():
                    ob = item['_object']
                    item[key] = get_portlet_assignment_xml(ob) or None
            yield item
