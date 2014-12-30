# -*- coding: utf-8 -*-
from transmogrifier.blueprints import ConditionalBlueprint
from venusianconfiguration import configure


@configure.transmogrifier.blueprint.component(name='plone.properties.get')
class GetProperties(ConditionalBlueprint):
    def __iter__(self):
        for item in self.previous:
            if self.condition(item):
                ob = item['_object']
                properties = [(key, (ob.getProperty(key), ob.getPropertyType(key))) for key in ob.propertyIds()] 
                item.update(dict(properties))
            yield item
