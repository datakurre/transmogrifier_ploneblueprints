# -*- coding: utf-8 -*-
from email.encoders import encode_base64
from email.message import Message

from plone import api
from Products.Archetypes.Marshall import RFC822Marshaller
from plone.dexterity.interfaces import IDexterityFTI
from plone.dexterity.utils import iterSchemata
from plone.rfc822 import initializeObjectFromSchemata
from plone.rfc822 import constructMessageFromSchemata
from venusianconfiguration import configure
from transmogrifier.blueprints import ConditionalBlueprint
from transmogrifier_ploneblueprints.utils import string_to_message
from transmogrifier_ploneblueprints.utils import message_to_string


def marshall(ob):
    types_tool = api.portal.get_tool('portal_types')
    fti = types_tool.get(ob.portal_type)
    if IDexterityFTI.providedBy(fti):
        # DX
        message = constructMessageFromSchemata(ob, iterSchemata(ob))
    else:
        # AT
        marshaller = RFC822Marshaller()
        marshaled = marshaller.marshall(ob)
        message = string_to_message(marshaled[2])
        message.set_charset('utf-8')
        encode_base64(message)
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
        initializeObjectFromSchemata(ob, iterSchemata(ob), message)
    else:
        # AT
        email_string = message_to_string(message)
        marshaller = RFC822Marshaller()
        marshaller.demarshall(ob, email_string)


@configure.transmogrifier.blueprint.component(name='plone.rfc822.demarshall')
class RFC822Demarshall(ConditionalBlueprint):
    def __iter__(self):
        portal = api.portal.get()
        for item in self.previous:
            if self.condition(item) and isinstance(item, Message):
                path = ''.join(portal.getPhysicalPath()) + item['_path']
                ob = portal.unrestrictedTraverse(path)
                demarshall(ob, item)
            yield item
