# -*- coding: utf-8 -*-
from Acquisition import aq_base
from transmogrifier.blueprints import ConditionalBlueprint
# noinspection PyUnresolvedReferences
from transmogrifier_ploneblueprints.utils import resolve_object
from venusianconfiguration import configure

import Acquisition


@configure.transmogrifier.blueprint.component(name='plone.properties.get')
class GetProperties(ConditionalBlueprint):
    def __iter__(self):
        context = self.transmogrifier.context
        for item in self.previous:
            if self.condition(item):
                obj = resolve_object(context, item)
                properties = [
                    (key, obj.getProperty(key), obj.getPropertyType(key))
                    for key in obj.propertyIds()
                    if hasattr(Acquisition.aq_base(obj), key)  # noqa
                ]
                item['_properties'] = properties

                if 'default_page' not in obj.propertyIds():
                    try:
                        default_page = Acquisition.aq_base(obj).default_page
                        obj['_properties'].append(
                            ('default_page', default_page, 'string'))
                    except AttributeError:
                        pass
            yield item


@configure.transmogrifier.blueprint.component(name='plone.properties.set')
class SetProperties(ConditionalBlueprint):
    def __iter__(self):
        context = self.transmogrifier.context
        for item in self.previous:
            if self.condition(item):
                obj = aq_base(resolve_object(context, item))
                props = item['_properties']
                for prop in props:
                    key, value, type_ = prop
                    if key == 'title':
                        continue
                    if key in obj.propertyIds():
                        obj.manage_changeProperties(**{key: value})
                        # what to do if type is different? Hope not...
                    else:
                        obj.manage_addProperty(key, value, type_)
            yield item
