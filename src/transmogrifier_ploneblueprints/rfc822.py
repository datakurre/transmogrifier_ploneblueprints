from Products.Archetypes.Marshall import RFC822Marshaller
from Products.CMFCore.utils import getToolByName
from plone.dexterity.interfaces import IDexterityFTI
from plone.dexterity.utils import iterSchemata
from plone.rfc822 import initializeObjectFromSchemata
from venusianconfiguration import configure
from transmogrifier.blueprints import ConditionalBlueprint
from email.message import Message

import logging
import email

logger = logging.getLogger('transmogrifier')

@configure.transmogrifier.blueprint.component(name='plone.rfc822.export')
class RFC822ExportSection(ConditionalBlueprint):
    def _add_message(self, item):
        key = self.options.get('key')
        if '_object' in item.keys() and key:
            portal_types = getToolByName(self.transmogrifier.context, 'portal_types')
            fti = portal_types.get(item['_type'])
            is_dexterity = IDexterityFTI.providedBy(fti)
            if is_dexterity:
                pass
            marshaller = RFC822Marshaller()
            marshalled = marshaller.marshall(item['_object'])
            message = email.message_from_string(marshalled[2])
            message.set_charset('utf-8')

            # convert list format
            for k, v in message.items():
                if '\r\n' in v:
                    value = v.replace('\r\n  ', '||')
                    message.replace_header(k, value)
            item[key] = message

    def __iter__(self):
        for item in self.previous:
            if self.condition(item):
                self._add_message(item)
            yield item

@configure.transmogrifier.blueprint.component(name='plone.rfc822.import')
class RFC822ImportSection(ConditionalBlueprint):
    def __iter__(self):
        for item in self.previous:
            if self.condition(item) and isinstance(item, Message):
                portal = self.transmogrifier.context
                path = "".join(portal.getPhysicalPath()) + item['_path']
                ob = portal.unrestrictedTraverse(path)
                initializeObjectFromSchemata(ob, iterSchemata(ob), item)
            yield item
