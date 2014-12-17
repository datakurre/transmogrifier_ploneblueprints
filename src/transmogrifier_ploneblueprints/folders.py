# -*- coding: utf-8 -*-
import importlib

# noinspection PyProtectedMember
from Products.Archetypes.ArchetypeTool import _types
from plone import api
from plone.dexterity.interfaces import IDexterityFTI
from venusianconfiguration import configure
from transmogrifier.blueprints import ConditionalBlueprint
from transmogrifier.utils import defaultMatcher
from transmogrifier_ploneblueprints.utils import pathsplit
from transmogrifier_ploneblueprints.utils import traverse


# collective/transmogrifier/sections/folders.py
# by rpatterson, optilude

# noinspection PyPep8Naming
@configure.transmogrifier.blueprint.component(name='plone.folders')
class Folders(ConditionalBlueprint):
    def __iter__(self):
        pathKeyMatcher = defaultMatcher(
            self.options, 'path-key', self.name, 'path')

        newPathKey = self.options.get('new-path-key', None)
        newTypeKey = self.options.get('new-type-key', '_type')
        folderType = self.options.get('folder-type', 'Folder')

        cache = self.options.get('cache', 'true').lower() == 'true'

        seen = set()

        for item in self.previous:
            if self.condition(item):
                keys = item.keys()
                pathKey = pathKeyMatcher(*keys)[0]

                if not pathKey:  # not enough info
                    yield item
                    continue

                newPathKey = newPathKey or pathKey
                newTypeKey = newTypeKey

                path = item[pathKey]
                elements = path.strip('/').rsplit('/', 1)
                container, id_ = (len(elements) == 1
                                  and ('', elements[0]) or elements)

                # This may be a new container
                if container not in seen:

                    container_path_items = list(pathsplit(container))
                    if container_path_items:

                        currentElement = []

                        # Check each possible parent folder
                        obj = self.transmogrifier.context
                        for element in container_path_items:
                            currentElement.append(element)
                            currentPath = '/'.join(currentElement)

                            if currentPath and currentPath not in seen:

                                if element and traverse(obj, element) is None:
                                    # We don't have this path - yield to create
                                    # a skeleton folder
                                    yield {newPathKey: '/' + currentPath,
                                           newTypeKey: folderType}
                                if cache:
                                    seen.add(currentPath)

                            obj = traverse(obj, element)

                if cache:
                    seen.add('{0:s}/{1:s}'.format(container, id_, ))
            yield item


def ensure_correct_class(ob):
    # TODO: Detect if class is changed into container type and initialize it
    types_tool = api.portal.get_tool('portal_types')
    fti = types_tool.get(ob.portal_type)
    if IDexterityFTI.providedBy(fti):
        module_name, class_name = fti.klass.rsplit('.', 1)
        module = importlib.import_module(module_name)
        klass = getattr(module, class_name)
    else:
        key = '.'.join([fti.product, fti.id])
        klass = _types[key]['klass']
    ob.__class__ = klass
    ob._p_changed = True


@configure.transmogrifier.blueprint.component(name='plone.class')
class Class(ConditionalBlueprint):
    def __iter__(self):
        portal = api.portal.get()
        for item in self.previous:
            if self.condition(item):
                try:
                    path = ''.join(portal.getPhysicalPath()) + item['_path']
                    ob = portal.unrestrictedTraverse(path)
                except KeyError:
                    pass
                else:
                    ensure_correct_class(ob)
            yield item
