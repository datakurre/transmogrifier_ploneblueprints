# -*- coding: utf-8 -*-
from plone import api
from plone.dexterity.interfaces import IDexterityContent
from plone.rfc822.defaultfields import BaseFieldMarshaler
from plone.rfc822.interfaces import IFieldMarshaler
from plone.uuid.interfaces import IUUID
from venusianconfiguration import configure
import pkg_resources
from zope.component import getUtility
from zope.interface import implementer

try:
    pkg_resources.get_distribution('z3c.relationfield')
except pkg_resources.DistributionNotFound:
    HAS_RELATIONFIELD = False
else:
    from zope.intid import IIntIds
    from z3c.relationfield.interfaces import IRelation
    from z3c.relationfield.interfaces import IRelationChoice
    from z3c.relationfield import RelationValue
    HAS_RELATIONFIELD = True


if HAS_RELATIONFIELD:
    @configure.adapter.factory(for_=(IDexterityContent, IRelation))
    @configure.adapter.factory(for_=(IDexterityContent, IRelationChoice))
    @implementer(IFieldMarshaler)
    class RelationFieldMarshaler(BaseFieldMarshaler):

        ascii = True

        def encode(self, value, charset='utf-8', primary=False):
            if value is None:
                return None
            if value.to_object is None:
                return None
            return IUUID(value.to_object)

        def decode(self, value, message=None, charset='utf-8',
                   contentType=None, primary=False):
            try:
                uuid = int(value.decode(charset))
            except TypeError, e:
                raise ValueError(e)

            intids = getUtility(IIntIds)
            portal_catalog = api.portal.get_tool('portal_catalog')
            for brain in portal_catalog.unrestrictedSearchResults(UID=uuid):
                # noinspection PyProtectedMember
                ob = brain._unrestrictedGetObject()
                intid = intids.queryObject(ob)
                if intid is None:
                    intid = intids.register(ob)
                return RelationValue(intid)
            return None
