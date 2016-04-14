# -*- coding: utf-8 -*-
from __future__ import absolute_import
from plone import api
from venusianconfiguration import configure
from transmogrifier.blueprints import ConditionalBlueprint
from transmogrifier_ploneblueprints.utils import traverse
from plone.uuid.interfaces import IUUID
from plone.uuid.interfaces import IMutableUUID

import Acquisition
import uuid
import pkg_resources

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


@configure.transmogrifier.blueprint.component(name='plone.uuid.get')
class GetUUID(ConditionalBlueprint):
    def __iter__(self):
        portal = api.portal.get()
        for item in self.previous:
            if self.condition(item):
                ob = traverse(portal, item['_path'])
                uuid_ = IUUID(ob, None)
                if uuid is not None:
                    item['_uuid'] = uuid_
                elif hasattr(Acquisition.aq_base(ob), 'UID'):
                    item['_uuid'] = Acquisition.aq_base(ob).UID()
                if not item.get('_uuid'):
                    item['_uuid'] = str(uuid.uuid4()).replace('-', '')
            yield item


# noinspection PyProtectedMember
def set_uuid(ob, uuid):
    types_tool = api.portal.get_tool('portal_types')
    fti = types_tool.get(ob.portal_type)
    if IDexterityFTI.providedBy(fti):
        # DX
        if HAS_DEXTERITY_REFERENCEABLE:
            if DX.IReferenceable.providedBy(ob):
                uid_catalog = api.portal.get_tool('uid_catalog')
                path = '/'.join(ob.getPhysicalPath())
                uid_catalog.uncatalog_object(path)
        # noinspection PyArgumentList
        IMutableUUID(ob).set(str(uuid))
        if HAS_DEXTERITY_REFERENCEABLE:
            if DX.IReferenceable.providedBy(ob):
                uid_catalog = api.portal.get_tool('uid_catalog')
                path = '/'.join(ob.getPhysicalPath())
                uid_catalog.catalog_object(ob, path)
    elif HAS_ARCHETYPES:
        if AT.IReferenceable.providedBy(ob):
            # AT
            ob._uncatalogUID(api.portal.get())
            ob._setUID(uuid)


@configure.transmogrifier.blueprint.component(name='plone.uuid.set')
class SetUUID(ConditionalBlueprint):
    def __iter__(self):
        portal = api.portal.get()
        for item in self.previous:
            if self.condition(item) and '_uuid' in item:
                set_uuid(traverse(portal, item['_path']), item['_uuid'])
            yield item
