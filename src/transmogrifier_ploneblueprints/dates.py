# -*- coding: utf-8 -*-
from plone import api
from transmogrifier.blueprints import ConditionalBlueprint
from transmogrifier_ploneblueprints.utils import traverse
from venusianconfiguration import configure

@configure.transmogrifier.blueprint.component(name='plone.fix_dates')
class FixDates(ConditionalBlueprint):
    def __iter__(self):
        portal = api.portal.get()
        for item in self.previous:
            if self.condition(item):
                ob = traverse(portal, item['_path'])
                if 'modification_date' in item:
                    ob.setModificationDate(item['modification_date'])
                if 'creation_date' in item:
                    try:
                        ob.setCreationDate(item['creation_date'])
                    except AttributeError:
                        # dexterity content does not have setCreationDate
                        ob.creation_date = item['creation_date']
            yield item
