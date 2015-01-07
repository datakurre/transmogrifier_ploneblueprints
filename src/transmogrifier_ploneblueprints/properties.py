# -*- coding: utf-8 -*-
from plone import api
from transmogrifier.blueprints import ConditionalBlueprint
from transmogrifier_ploneblueprints.utils import traverse
from venusianconfiguration import configure


@configure.transmogrifier.blueprint.component(name='plone.properties.get')
class GetProperties(ConditionalBlueprint):
    def __iter__(self):
        for item in self.previous:
            if self.condition(item):
                ob = item['_object']
                properties = [
                    (key, ob.getProperty(key), ob.getPropertyType(key))
                    for key in ob.propertyIds()
                ]
                item['_properties'] = properties
            yield item


@configure.transmogrifier.blueprint.component(name='plone.properties.set')
class SetProperties(ConditionalBlueprint):
    def __iter__(self):
        portal = api.portal.get()
        for item in self.previous:
            if self.condition(item):
                ob = traverse(portal, item['_path'])
                props = item['_properties']
                for prop in props:
                    key, value, type_ = prop
                    if key == 'title':
                        continue
                    if key in ob.propertyIds():
                        ob.manage_changeProperties(**{key: value})
                        # what to do if type is different?
                    else:
                        ob.manage_addProperty(key, value, type_)
            yield item
