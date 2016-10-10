# -*- coding: utf-8 -*-
from plone import api
from transmogrifier.blueprints import ConditionalBlueprint
from transmogrifier.utils import defaultMatcher
from transmogrifier_ploneblueprints.utils import explicit_traverse
from transmogrifier_ploneblueprints.utils import pathsplit
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


# collective/transmogrifier/sections/folders.py
# by rpatterson, optilude

def folders(item, path_key_matcher, new_path_key, new_type_key, folder_type,
            cache, seen):
    keys = item.keys()
    path_key = path_key_matcher(*keys)[0]

    if not path_key:  # not enough info
        return

    new_path_key = new_path_key or path_key

    path = item[path_key]
    elements = path.strip('/').rsplit('/', 1)
    container, id_ = (len(elements) == 1 and
                      ('', elements[0]) or elements)

    # This may be a new container
    if container not in seen:

        container_path_items = list(pathsplit(container))
        if container_path_items:

            checked_elements = []

            # Check each possible parent folder
            obj = api.portal.get()
            for element in container_path_items:
                checked_elements.append(element)
                current_path = '/'.join(checked_elements)

                if current_path and current_path not in seen:

                    if element and explicit_traverse(obj, element) is None:
                        # We don't have this path - yield to create
                        # a skeleton folder
                        yield {new_path_key: '/' + current_path,
                               new_type_key: folder_type}
                    if cache:
                        seen.add(current_path)

                obj = explicit_traverse(obj, element)

    if cache:
        seen.add('{0:s}/{1:s}'.format(container, id_, ))


# noinspection PyPep8Naming
@configure.transmogrifier.blueprint.component(name='plone.folders')
class Folders(ConditionalBlueprint):
    def __iter__(self):
        path_key = defaultMatcher(self.options, 'path-key', self.name, 'path')

        new_path_key = self.options.get('new-path-key', None)
        new_type_key = self.options.get('new-type-key', '_type')
        folder_type = self.options.get('folder-type', 'Folder')
        cache = self.options.get('cache', 'true').lower() == 'true'

        seen = set()

        for item in self.previous:
            if self.condition(item):
                for folder_item in folders(item, path_key,
                                           new_path_key, new_type_key,
                                           folder_type, cache, seen):
                    yield folder_item
            yield item


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
