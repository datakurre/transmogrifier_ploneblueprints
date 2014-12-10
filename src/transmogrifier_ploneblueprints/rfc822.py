from Products.Archetypes.Marshall import RFC822Marshaller
from venusianconfiguration import configure
from transmogrifier.blueprints import ConditionalBlueprint

import logging
import email

logger = logging.getLogger('transmogrifier')

@configure.transmogrifier.blueprint.component(name='plone.atrfc822')
class ATRFC822Section(ConditionalBlueprint):
    def _add_message(self, item):
        key = self.options.get('key')
        if '_object' in item.keys() and key:
            marshaller = RFC822Marshaller()
            marshalled = marshaller.marshall(item['_object'])
            message = email.message_from_string(marshalled[2])

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

