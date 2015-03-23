# -*- coding: utf-8 -*-
import importlib
import Acquisition

from plone import api
from plone.dexterity.interfaces import IDexterityFTI
from venusianconfiguration import configure
from transmogrifier.blueprints import ConditionalBlueprint
from transmogrifier.utils import defaultMatcher
from transmogrifier_ploneblueprints.utils import pathsplit
from transmogrifier_ploneblueprints.utils import traverse

import pkg_resources

try:
    pkg_resources.get_distribution('Products.Archetypes')
except pkg_resources.DistributionNotFound:
    HAS_ARCHETYPES = False
else:
    # noinspection PyProtectedMember
    from Products.Archetypes.ArchetypeTool import _types
    HAS_ARCHETYPES = True


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
    container, id_ = (len(elements) == 1
                      and ('', elements[0]) or elements)

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

                    if element and traverse(obj, element) is None:
                        # We don't have this path - yield to create
                        # a skeleton folder
                        yield {new_path_key: '/' + current_path,
                               new_type_key: folder_type}
                    if cache:
                        seen.add(current_path)

                obj = traverse(obj, element)

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


def ensure_correct_class(ob):
    # TODO: Detect if class is changed into container type and initialize it
    types_tool = api.portal.get_tool('portal_types')
    fti = types_tool.get(ob.portal_type)
    if IDexterityFTI.providedBy(fti):
        module_name, class_name = fti.klass.rsplit('.', 1)
        module = importlib.import_module(module_name)
        klass = getattr(module, class_name)
    elif HAS_ARCHETYPES:
        key = '.'.join([fti.product, fti.id])
        klass = _types.get(key, {}).get('klass', None)
    if klass is not None and ob.__class__ != klass:
        ob.__class__ = klass
        ob._p_changed = True

        # XXX: This may not work or may have strange side-effects:
        #
        # http://blog.redturtle.it/2013/02/25/
        # migrating-dexterity-items-to-dexterity-containers
        #
        # This would work if the class change is done before the
        # wrong class is committed. Also, this has been seen to work
        # when the target object does not have any children yet.


@configure.transmogrifier.blueprint.component(name='plone.gopip.get')
class GetObjectPositionInParent(ConditionalBlueprint):
    # noinspection PyUnresolvedReferences
    def __iter__(self):
        key = self.options.get('key', '_gopip')
        for item in self.previous:
            if self.condition(item):
                if '_object' in item and key:
                    ob = item['_object']
                    id_ = ob.getId()
                    parent = Acquisition.aq_parent(ob)
                    if hasattr(Acquisition.aq_base(ob), 'getObjectPosition'):
                        item[key] = parent.getObjectPosition(id_)
                    else:
                        item[key] = None
            yield item


@configure.transmogrifier.blueprint.component(name='plone.gopip.set')
class SetObjectPositionInParent(ConditionalBlueprint):
    # noinspection PyUnresolvedReferences
    def __iter__(self):
        portal = api.portal.get()
        key = self.options.get('key', '_gopip')
        for item in self.previous:
            if self.condition(item):
                position = item.get(key)
                if position is None:
                    continue
                try:
                    ob = traverse(portal, item['_path'])
                except KeyError:
                    pass
                if ob:
                    id_ = ob.getId()
                    parent = Acquisition.aq_parent(ob)
                    if hasattr(Acquisition.aq_base(parent),
                               'moveObjectToPosition'):
                        parent.moveObjectToPosition(
                            id_, position, suppress_events=False)
            yield item


@configure.transmogrifier.blueprint.component(name='plone.portal_type')
class PortalType(ConditionalBlueprint):
    def __iter__(self):
        portal = api.portal.get()
        key = self.options.get('key', '_type')
        folder_type = self.options.get('folder-type', 'Folder')
        for item in self.previous:
            if self.condition(item):
                try:
                    ob = traverse(portal, item['_path'])
                    portal_type = item[key]
                except KeyError:
                    pass
                else:
                    if ob is portal or portal_type == folder_type:
                        # Skip folder_type, because Folders-blueprint
                        # would cause all folderish-types to be b0rked
                        continue
                    ob.portal_type = portal_type
                    ensure_correct_class(ob)
            yield item
