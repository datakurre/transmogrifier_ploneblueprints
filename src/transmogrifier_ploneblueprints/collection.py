# -*- coding: utf-8 -*-
from __future__ import absolute_import
from plone import api
from venusianconfiguration import configure
from transmogrifier.blueprints import ConditionalBlueprint
from transmogrifier_ploneblueprints.utils import traverse


@configure.transmogrifier.blueprint.component(name='plone.collection.subcollection')
class Subcollection(ConditionalBlueprint):
    def __iter__(self):
        portal = api.portal.get()
        for item in self.previous:
            if self.condition(item):
                try:
                    context = traverse(portal, 
                        '/'.join(item['_path'].split('/')[:-1]))
                except KeyError:
                    yield item
                    continue

                if all([context.portal_type == 'Collection', 
                        item['_type'] == 'Collection']):
                    path_parts = item['_path'].split('/')
                    new_path = ('/'.join(path_parts[:-2]) + '/' + 
                                path_parts[-2] + '-' + path_parts[-1])
                    try:
                        item.replace_header('_path', new_path)
                    # in the case we have dict instead of Message
                    except AttributeError:
                        item['_path'] = new_path
                 
            yield item
