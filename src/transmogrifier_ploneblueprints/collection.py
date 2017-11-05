# -*- coding: utf-8 -*-
from __future__ import absolute_import
from Acquisition import aq_base
from transmogrifier.blueprints.base import Blueprint
from transmogrifier_ploneblueprints.utils import resolve_object
from venusianconfiguration import configure


@configure.transmogrifier.blueprint.component(name='plone.collection.flatten_subcollections')  # noqa
class FlattenSubcollections(Blueprint):
    def __iter__(self):
        context = self.transmogrifier.context
        for item in self.previous:
            if item.get('_type') in ['Collection', 'Topic']:
                try:
                    obj = aq_base(resolve_object(context, dict(
                        _path='/'.join(item['_path'].split('/')[:-1])),
                        default=None))
                except AssertionError:
                    obj = None

                if obj and all([obj.portal_type in ['Collection', 'Topic'],
                               item['_type'] in ['Collection', 'Topic']]):
                    path_parts = item['_path'].split('/')
                    new_path = ('/'.join(path_parts[:-2]) + '/' +
                                path_parts[-2] + '-' + path_parts[-1])
                    item['_type'] = 'Collection'
                    item['_path'] = new_path

            yield item
