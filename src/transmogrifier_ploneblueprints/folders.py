# -*- coding: utf-8 -*-
from plone import api
from transmogrifier.blueprints import ConditionalBlueprint
from venusianconfiguration import configure

import Acquisition
import pkg_resources


try:
    pkg_resources.get_distribution('Products.Archetypes')
except pkg_resources.DistributionNotFound:
    HAS_ARCHETYPES = False
else:
    # noinspection PyProtectedMember
    HAS_ARCHETYPES = True

try:
    pkg_resources.get_distribution('plone.dexterity')
except pkg_resources.DistributionNotFound:
    HAS_DEXTERITY = False


@configure.transmogrifier.blueprint.component(name='plone.folders.gopip.get')
class GetObjectPositionInParent(ConditionalBlueprint):
    # noinspection PyUnresolvedReferences
    def __iter__(self):
        key = self.options.get('key', '_gopip')
        for item in self.previous:
            if self.condition(item):
                if '_object' in item and key:
                    obj = item['_object']
                    id_ = obj.getId()
                    parent = Acquisition.aq_parent(obj)
                    if hasattr(Acquisition.aq_base(parent),
                               'getObjectPosition'):
                        item[key] = parent.getObjectPosition(id_)
                    else:
                        item[key] = None
            yield item


@configure.transmogrifier.blueprint.component(name='plone.folders.gopip.set')
class SetObjectPositionInParent(ConditionalBlueprint):
    # noinspection PyUnresolvedReferences
    def __iter__(self):
        key = self.options.get('key', '_gopip')
        for item in self.previous:
            position = item.get(key)
            if self.condition(item) and position is not None:
                obj = api.content.get(item['_path'])
                if obj:
                    id_ = obj.getId()
                    parent = Acquisition.aq_parent(obj)
                    if hasattr(Acquisition.aq_base(parent),
                               'moveObjectToPosition'):
                        parent.moveObjectToPosition(
                            id_, position, suppress_events=False)
            yield item
