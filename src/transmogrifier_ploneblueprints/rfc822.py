# -*- coding: utf-8 -*-
from email.message import Message
import Acquisition

import pkg_resources
from plone import api
from plone.dexterity.interfaces import IDexterityFTI
from plone.dexterity.utils import iterSchemata
from plone.rfc822 import initializeObject
from plone.rfc822 import initializeObjectFromSchemata
from plone.rfc822 import constructMessage
from plone.rfc822 import constructMessageFromSchemata
from transmogrifier_ploneblueprints.utils import traverse
from venusianconfiguration import configure
from transmogrifier.blueprints import ConditionalBlueprint

try:
    pkg_resources.get_distribution('Products.Archetypes')
except pkg_resources.DistributionNotFound:
    HAS_ARCHETYPES = False
else:
    from collective.atrfc822.fields import iterFields
    HAS_ARCHETYPES = True


def marshall(ob):
    types_tool = api.portal.get_tool('portal_types')
    fti = types_tool.get(ob.portal_type)
    # noinspection PyUnresolvedReferences
    if IDexterityFTI.providedBy(fti):
        # DX
        message = constructMessageFromSchemata(ob, iterSchemata(ob))
    elif HAS_ARCHETYPES and hasattr(Acquisition.aq_base(ob), 'schema'):
        # AT
        message = constructMessage(ob, iterFields(ob))
    else:
        # Other
        schemata = tuple(ob.__provides__.interfaces())
        message = constructMessageFromSchemata(ob, schemata)
    return message


@configure.transmogrifier.blueprint.component(name='plone.rfc822.marshall')
class RFC822Marshall(ConditionalBlueprint):
    def __iter__(self):
        key = self.options.get('key')
        for item in self.previous:
            if self.condition(item):
                if '_object' in item and key:
                    item[key] = marshall(item['_object'])
            yield item


def demarshall(ob, message):
    types_tool = api.portal.get_tool('portal_types')
    fti = types_tool.get(ob.portal_type)
    if IDexterityFTI.providedBy(fti):
        # DX
        try:
            initializeObjectFromSchemata(ob, iterSchemata(ob), message)
        except Exception as e:
            import pdb; pdb.set_trace()
            initializeObjectFromSchemata(ob, iterSchemata(ob), message)
    elif HAS_ARCHETYPES:
        # AT
        initializeObject(ob, iterFields(ob), message)


@configure.transmogrifier.blueprint.component(name='plone.rfc822.demarshall')
class RFC822Demarshall(ConditionalBlueprint):
    def __iter__(self):
        portal = api.portal.get()
        for item in self.previous:
            if self.condition(item) and isinstance(item, Message):
                ob = traverse(portal, item['_path'])
                demarshall(ob, item)
            yield item
