import base64
from email.encoders import encode_base64
from Products.Archetypes.Marshall import RFC822Marshaller
from Products.CMFCore.utils import getToolByName
from plone.dexterity.interfaces import IDexterityFTI
from plone.dexterity.utils import iterSchemata
from plone.rfc822 import initializeObjectFromSchemata, \
    constructMessageFromSchemata
from venusianconfiguration import configure
from transmogrifier.blueprints import ConditionalBlueprint
from email.message import Message

import logging
from transmogrifier_ploneblueprints.utils import string_to_message, \
    message_to_string

logger = logging.getLogger('transmogrifier')

@configure.transmogrifier.blueprint.component(name='plone.rfc822.export')
class RFC822ExportSection(ConditionalBlueprint):
    def _add_message(self, item):
        key = self.options.get('key')
        if '_object' in item.keys() and key:
            ob = item['_object']
            portal_types = getToolByName(self.transmogrifier.context,
                                         'portal_types')
            fti = portal_types.get(item['_type'])
            is_dexterity = IDexterityFTI.providedBy(fti)

            if is_dexterity:
                message = constructMessageFromSchemata(ob, iterSchemata(ob))
            else:
                marshaller = RFC822Marshaller()
                marshalled = marshaller.marshall(ob)
                message = string_to_message(marshalled[2])
		message.set_charset('utf-8')
                encode_base64(message)
            item[key] = message

    def __iter__(self):
        for item in self.previous:
            if self.condition(item):
                self._add_message(item)
            yield item


@configure.transmogrifier.blueprint.component(name='plone.rfc822.import')
class RFC822ImportSection(ConditionalBlueprint):
    def _update_schema(self, ob, item):
        portal_types = getToolByName(self.transmogrifier.context,
                                     'portal_types')
        fti = portal_types.get(item['_type'])
        is_dexterity = IDexterityFTI.providedBy(fti)

        if is_dexterity:
            initializeObjectFromSchemata(ob, iterSchemata(ob), item)
        else:
            email_string = message_to_string(item)
            marshaller = RFC822Marshaller()
            marshaller.demarshall(ob, email_string)


    def __iter__(self):
        for item in self.previous:
            if self.condition(item) and isinstance(item, Message):
                portal = self.transmogrifier.context
                path = "".join(portal.getPhysicalPath()) + item['_path']
                ob = portal.unrestrictedTraverse(path)
                self._update_schema(ob, item)
            yield item
