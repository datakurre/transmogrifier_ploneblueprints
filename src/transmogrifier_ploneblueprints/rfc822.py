# -*- coding: utf-8 -*-
from email.message import Message
from plone import api
from plone.rfc822 import constructMessage
from plone.rfc822 import constructMessageFromSchemata
from plone.rfc822 import initializeObject
from plone.rfc822 import initializeObjectFromSchemata
from plone.rfc822.defaultfields import UnicodeValueFieldMarshaler
from plone.rfc822.interfaces import IFieldMarshaler
from plone.rfc822.interfaces import IPrimaryField
from transmogrifier.blueprints import ConditionalBlueprint
from transmogrifier_ploneblueprints.utils import resolve_object
from venusianconfiguration import configure
from zope.component import adapter
from zope.interface import alsoProvides
from zope.interface import implementer
from zope.schema.interfaces import IChoice

import Acquisition
import logging
import pkg_resources


logger = logging.getLogger('transmogrifier')


try:
    pkg_resources.get_distribution('Products.Archetypes')
except pkg_resources.DistributionNotFound:
    HAS_ARCHETYPES = False
else:
    from collective.atrfc822.fields import iterFields
    HAS_ARCHETYPES = True


try:
    pkg_resources.get_distribution('plone.dexterity')
    from plone.app.dexterity.behaviors.metadata import IDublinCore
    from plone.app.dexterity.behaviors.metadata import DublinCore
except pkg_resources.DistributionNotFound:
    HAS_DEXTERITY = False

    class IDexterityFTI(object):
        """Mock"""

    class IDexterityContent(object):
        """Mock"""
else:
    from plone.dexterity.interfaces import IDexterityFTI
    from plone.dexterity.interfaces import IDexterityContent
    from plone.dexterity.utils import iterSchemata
    HAS_DEXTERITY = True


try:
    pkg_resources.get_distribution('plone.app.contenttypes')
except pkg_resources.DistributionNotFound:
    HAS_PAC = False
else:
    from plone.app.contenttypes.behaviors.leadimage import ILeadImage
    alsoProvides(ILeadImage['image'], IPrimaryField)
    HAS_PAC = True


def marshall(obj):
    types_tool = api.portal.get_tool('portal_types')
    fti = types_tool.get(obj.portal_type)
    # noinspection PyUnresolvedReferences
    if HAS_DEXTERITY and IDexterityFTI.providedBy(fti):
        # DX
        message = constructMessageFromSchemata(obj, iterSchemata(obj))
        # Ensure that all DC fields are included
        dc = constructMessageFromSchemata(DublinCore(obj), [IDublinCore])
        for name in [key for key in dc.keys() if not message[key]]:
            if name in message.keys():
                del message[name]
            message[name] = dc[name]
    elif HAS_ARCHETYPES and hasattr(Acquisition.aq_base(obj), 'schema'):
        # AT
        message = constructMessage(obj, iterFields(obj))
    else:
        # Other
        schemata = tuple(obj.__provides__.interfaces())
        message = constructMessageFromSchemata(obj, schemata)
    return message


@configure.transmogrifier.blueprint.component(name='plone.rfc822.marshall')
class RFC822Marshall(ConditionalBlueprint):
    def __iter__(self):
        context = self.transmogrifier.context
        key = self.options.get('key')
        for item in self.previous:
            if self.condition(item):
                obj = resolve_object(context, item)
                item[key] = marshall(obj)
            yield item


def demarshall(obj, message):
    types_tool = api.portal.get_tool('portal_types')
    fti = types_tool.get(obj.portal_type)
    if IDexterityFTI.providedBy(fti):
        # DX
        payload = message._payload
        message._payload = None
        initializeObjectFromSchemata(DublinCore(obj), [IDublinCore], message)
        message._payload = payload
        initializeObjectFromSchemata(obj, iterSchemata(obj), message)
    elif HAS_ARCHETYPES:
        # AT
        initializeObject(obj, iterFields(obj), message)


@configure.transmogrifier.blueprint.component(name='plone.rfc822.demarshall')
class RFC822Demarshall(ConditionalBlueprint):
    def __iter__(self):
        context = self.transmogrifier.context
        key = self.options.get('key')
        for item in self.previous:
            message = item.get(key)
            if self.condition(item) and isinstance(message, Message):
                obj = resolve_object(context, item)
                demarshall(obj, message)
            yield item


@implementer(IFieldMarshaler)
@adapter(IDexterityContent, IChoice)
class ChoiceValueFieldMarshaler(UnicodeValueFieldMarshaler):
    # noinspection PyPep8Naming
    def decode(self, value, message=None, charset='utf-8', contentType=None,
               primary=False):
        try:
            return super(ChoiceValueFieldMarshaler, self).decode(
                value, message=message, charset=charset,
                contentType=contentType, primary=primary)
        except ValueError:
            # Fixes issues with allow_discussion-field
            try:
                return self.field.vocabulary.getTermByToken(value).value
            except LookupError as e:
                logger.warning('LookupError: {0:s}'.format(str(e)))
                return None
