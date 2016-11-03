# -*- coding: utf-8 -*-
from __future__ import absolute_import
from plone import api
from plone.uuid.interfaces import IMutableUUID
from plone.uuid.interfaces import IUUID
from transmogrifier.blueprints import ConditionalBlueprint
from transmogrifier_ploneblueprints.utils import resolve_object
from venusianconfiguration import configure

import Acquisition
import pkg_resources
import uuid


try:
    pkg_resources.get_distribution('Products.Archetypes')
except pkg_resources.DistributionNotFound:
    HAS_ARCHETYPES = False
else:
    from Products.Archetypes import interfaces as AT
    HAS_ARCHETYPES = True

try:
    pkg_resources.get_distribution('plone.dexterity')
except pkg_resources.DistributionNotFound:
    HAS_DEXTERITY = False

    class IDexterityFTI(object):
        """Mock"""
else:
    from plone.dexterity.interfaces import IDexterityFTI
    HAS_DEXTERITY = True

try:
    pkg_resources.get_distribution('plone.app.referenceablebehavior')
except pkg_resources.DistributionNotFound:
    HAS_DEXTERITY_REFERENCEABLE = False
else:
    from plone.app.referenceablebehavior import interfaces as DX
    HAS_DEXTERITY_REFERENCEABLE = True


@configure.transmogrifier.blueprint.component(name='plone.uuid.path_from_uuid')
class GetPathFromUUID(ConditionalBlueprint):
    def __iter__(self):
        portal = api.portal.get()
        portal_path = '/'.join(portal.getPhysicalPath())
        pc = api.portal.get_tool('portal_catalog')
        for item in self.previous:
            if self.condition(item):
                uuid_ = item['_uuid']
                uuid_brains = (
                    uuid_ and
                    pc.unrestrictedSearchResults(UID=uuid_) or
                    [])

                parent_uuid_ = item['_parent_uuid']
                parent_uuid_brains = (
                    parent_uuid_ and
                    pc.unrestrictedSearchResults(UID=parent_uuid_) or
                    [])

                if uuid_brains:
                    for brain in uuid_brains:
                        del item['_path']
                        item['_path'] = brain.getPath()[len(portal_path):]

                elif parent_uuid_brains:
                    for brain in parent_uuid_brains:
                        path_ = item['_path']
                        del item['_path']
                        item['_path'] = (brain.getPath()[len(portal_path):] +
                                         '/' + path_.split('/')[-1])

            yield item


# noinspection PyUnresolvedReferences
@configure.transmogrifier.blueprint.component(name='plone.uuid.get_parent')
class GetParentUUID(ConditionalBlueprint):
    def __iter__(self):
        context = self.transmogrifier.context
        for item in self.previous:
            if self.condition(item):
                obj = resolve_object(context, item)
                parent = Acquisition.aq_parent(obj)
                uuid_ = IUUID(parent, None)
                if uuid_ is not None:
                    item['_parent_uuid'] = uuid_
                elif hasattr(Acquisition.aq_base(parent), 'UID'):
                    item['_parent_uuid'] = Acquisition.aq_base(parent).UID()
                if not item.get('_parent_uuid'):
                    item['_parent_uuid'] = None
            yield item


# noinspection PyUnresolvedReferences
@configure.transmogrifier.blueprint.component(name='plone.uuid.get')
class GetUUID(ConditionalBlueprint):
    def __iter__(self):
        context = self.transmogrifier.context
        for item in self.previous:
            if self.condition(item):
                obj = resolve_object(context, item)
                uuid_ = IUUID(obj, None)
                if uuid_ is not None:
                    item['_uuid'] = uuid_
                elif hasattr(Acquisition.aq_base(obj), 'UID'):
                    item['_uuid'] = Acquisition.aq_base(obj).UID()
                if not item.get('_uuid'):
                    item['_uuid'] = str(uuid.uuid4()).replace('-', '')
            yield item


# noinspection PyProtectedMember
def set_uuid(obj, uuid):
    types_tool = api.portal.get_tool('portal_types')
    fti = types_tool.get(obj.portal_type)
    if IDexterityFTI.providedBy(fti):
        # DX
        if HAS_DEXTERITY_REFERENCEABLE:
            if DX.IReferenceable.providedBy(obj):
                uid_catalog = api.portal.get_tool('uid_catalog')
                path = '/'.join(obj.getPhysicalPath())
                uid_catalog.uncatalog_object(path)
        # noinspection PyArgumentList
        IMutableUUID(obj).set(str(uuid))
        if HAS_DEXTERITY_REFERENCEABLE:
            if DX.IReferenceable.providedBy(obj):
                uid_catalog = api.portal.get_tool('uid_catalog')
                path = '/'.join(obj.getPhysicalPath())
                uid_catalog.catalog_object(obj, path)
    elif HAS_ARCHETYPES:
        if AT.IReferenceable.providedBy(obj):
            # AT
            obj._uncatalogUID(api.portal.get())
            obj._setUID(uuid)


@configure.transmogrifier.blueprint.component(name='plone.uuid.set')
class SetUUID(ConditionalBlueprint):
    def __iter__(self):
        context = self.transmogrifier.context
        for item in self.previous:
            if self.condition(item) and '_uuid' in item:
                obj = resolve_object(context, item)
                set_uuid(obj, item['_uuid'])
            yield item
