# -*- coding: utf-8 -*-
from email.message import Message

import Acquisition
import pkg_resources
from plone import api
from plone.rfc822 import initializeObject
from plone.rfc822 import initializeObjectFromSchemata
from plone.rfc822 import constructMessage
from plone.rfc822 import constructMessageFromSchemata
from plone.rfc822.defaultfields import UnicodeValueFieldMarshaler
from plone.rfc822.interfaces import IFieldMarshaler
from plone.rfc822.interfaces import IPrimaryField
from zope.component import adapter
from zope.interface import implementer
from zope.interface import alsoProvides
from venusianconfiguration import configure
from zope.schema.interfaces import IChoice

from transmogrifier_ploneblueprints.utils import traverse
from transmogrifier.blueprints import ConditionalBlueprint

import logging
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
        except Exception:
            raise
#           import pdb; pdb.set_trace()
#           initializeObjectFromSchemata(ob, iterSchemata(ob), message)
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
                if ob is not portal:
                    demarshall(ob, item)
            yield item


@configure.adapter.factory()
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
