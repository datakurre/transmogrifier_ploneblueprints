# -*- coding: utf-8 -*-
from plone import api
from transmogrifier.blueprints import ConditionalBlueprint
from venusianconfiguration import configure


@configure.transmogrifier.blueprint.component(name='plone.reindex_object')
class ReindexObject(ConditionalBlueprint):
    def __iter__(self):
        indexes = api.portal.get_tool('portal_catalog').indexes()
        for item in self.previous:
            if self.condition(item):
                ob = api.content.get(path=item['_path'])
                ob.reindexObject(idxs=indexes)
                ob.reindexObjectSecurity()
            yield item
