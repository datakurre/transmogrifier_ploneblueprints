# -*- coding: utf-8 -*-
from plone.dexterity.interfaces import IDexterityContent
from plone.rfc822.defaultfields import UnicodeValueFieldMarshaler
from plone.rfc822.interfaces import IFieldMarshaler
from venusianconfiguration import configure
from zope.component import adapter
from zope.interface import implementer
from zope.schema.interfaces import IChoice


@configure.adapter.factory()
@implementer(IFieldMarshaler)
@adapter(IDexterityContent, IChoice)
class ChoiceValueFieldMarshaler(UnicodeValueFieldMarshaler):
    def decode(self, value, message=None, charset='utf-8', contentType=None,
               primary=False):
        try:
            return super(ChoiceValueFieldMarshaler, self).decode(
                value, message=message, charset=charset,
                contentType=contentType, primary=primary)
        except ValueError:
            # Fixes issues with allow_discussion-field
            return self.field.vocabulary.getTermByToken(value).value
