# -* coding: utf-8 -*-
from plone import api
from transmogrifier.blueprints import ConditionalBlueprint
from transmogrifier.utils import defaultMatcher
from transmogrifier.utils import to_boolean
# based on collective/transmogrifier/sections/constructor.py
# by rpatterson, regebro, mjpieters, optilude, csenger
from transmogrifier_ploneblueprints.utils import traverse
from venusianconfiguration import configure

import logging
import posixpath


logger = logging.getLogger('transmogrifier')


def cleanup(obj):
    for obj_id in obj.objectIds():
        try:
            obj.manage_delObjects([obj_id])
        except Exception as e:
            logger.warn('Unable to clean %s because of %s' %
                        (obj[obj_id], e))


def constructInstance(context, item,
                      type_key_matcher, path_key_matcher, purge=False):

    keys = item.keys()
    type_key = type_key_matcher(*keys)[0]
    path_key = path_key_matcher(*keys)[0]

    if not (type_key and path_key):  # not enough info
        return

    type_, path = item[type_key], str(item[path_key])
    portal_path = '/'.join(api.portal.get().getPhysicalPath())

    if path == '/' or path.rstrip(posixpath.sep) == portal_path:
        container, id_ = posixpath.split(portal_path)
        obj = api.portal.get()
    else:
        container, id_ = posixpath.split(path.strip(posixpath.sep))
        container = posixpath.sep + container  # abs path
        obj = traverse(context, posixpath.join(container, id_))

    if obj is None:
        parent = traverse(context, container)
        if parent is None and container == portal_path:
            parent = api.portal.get()
        assert parent is not None, (
            'Container %s does not exist for item %s' %
            (container, path))
        obj = api.content.create(parent, type=type_, id=id_)
        cleanup(obj)  # always purge new objects

    item[path_key] = '/'.join(obj.getPhysicalPath())[len(portal_path):]

    if purge and obj.objectIds():
        cleanup(obj)

    return obj


@configure.transmogrifier.blueprint.component(name='plone.constructor')
class Constructor(ConditionalBlueprint):
    def __iter__(self):
        context = self.transmogrifier.context

        type_key = defaultMatcher(
            self.options, 'type-key', self.name, 'type', ('portal_type', 'Type'))  # noqa
        path_key = defaultMatcher(
            self.options, 'path-key', self.name, 'path')

        purge = to_boolean(self.options.get('purge', False))
        object_key = self.options.get('object-key', '_object')

        for item in self.previous:
            if self.condition(item):
                obj = constructInstance(
                    context, item, type_key, path_key, purge)
                item[object_key] = obj
            yield item
