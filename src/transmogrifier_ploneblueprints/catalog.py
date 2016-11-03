# -*- coding: utf-8 -*-
from plone import api
from transmogrifier.blueprints import ConditionalBlueprint
from transmogrifier_ploneblueprints.utils import resolve_object
from venusianconfiguration import configure


@configure.transmogrifier.blueprint.component(name='plone.reindex_object')
class ReindexObject(ConditionalBlueprint):
    def __iter__(self):
        context = self.transmogrifier.context
        indexes = api.portal.get_tool('portal_catalog').indexes()
        for item in self.previous:
            if self.condition(item):
                obj = resolve_object(context, item)
                obj.reindexObject(idxs=indexes)
            yield item
