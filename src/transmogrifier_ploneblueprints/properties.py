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
                properties = [(key, ob.getProperty(key), ob.getPropertyType(key)) 
                              for key in ob.propertyIds()] 
                item['properties'] = properties
            yield item

@configure.transmogrifier.blueprint.component(name='plone.properties.set')
class SetProperties(ConditionalBlueprint):
    def __iter__(self):
        portal = api.portal.get()
        for item in self.previous:
            if self.condition(item):
                ob = traverse(portal, item['_path'])
                # set properties
            yield item
