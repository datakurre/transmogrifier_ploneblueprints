# -*- coding: utf-8 -*-
from __future__ import print_function
from plone import api
from transmogrifier.blueprints import ConditionalBlueprint
from transmogrifier.utils import defaultMatcher
from transmogrifier_ploneblueprints.utils import explicit_traverse
from venusianconfiguration import configure

import Acquisition
import logging
import posixpath


# from collective/transmogrifier/sections/constructor.py
# by rpatterson, regebro, mjpieters, optilude, csenger

logger = logging.getLogger('transmogrifier')


def _constructInstance(fti, context, id_):
    try:
        obj = fti._constructInstance(context, id_)
    except Exception:
        import traceback
        traceback.print_exc()
        print('Fix issue manually and continue to retry...')
        import pdb
        pdb.set_trace()
        obj = fti._constructInstance(context, id_)
    return obj


def cleanup(obj):
    for obj_id in obj.objectIds():
        try:
            obj.manage_delObjects([obj_id])
        except Exception as e:
            logger.warn('Unable to clean %s because of %s' % (
                obj[obj_id], e
            ))


def constructInstance(item, type_key_matcher, path_key_matcher,
                      required, empty=True):
    portal = api.portal.get()
    types_tool = api.portal.get_tool('portal_types')

    keys = item.keys()
    type_key = type_key_matcher(*keys)[0]
    path_key = path_key_matcher(*keys)[0]

    if not (type_key and path_key):  # not enough info
        return

    type_, path = item[type_key], item[path_key]

    fti = types_tool.getTypeInfo(type_)
    if fti is None:  # not an existing type
        return

    assert fti is not None, (
        u'Portal type "{0:s}" not available.'.format(type_))

    path = path.encode('ASCII')
    container, id_ = posixpath.split(path.strip('/'))

    if not id_:  # site root should exist
        return

    context = explicit_traverse(portal, container, None)
    if context is None:
        error = 'Container %s does not exist for item %s' % (
            container, path)
        if required:
            raise KeyError(error)
        logger.warn(error)
        return

    # noinspection PyUnresolvedeferences
    exists = getattr(Acquisition.aq_base(context), id_, None)
    if getattr(exists, 'id', None) == id_:
        return

    obj = _constructInstance(fti, context, id_)

    # For CMF <= 2.1 (aka Plone 3)
    if hasattr(fti, '_finishConstruction'):
        # noinspection PyProtectedMember
        obj = fti._finishConstruction(obj)

    if obj.getId() != id_:
        item[path_key] = posixpath.join(container, obj.getId())

    if empty and obj.objectIds():
        cleanup(obj)


@configure.transmogrifier.blueprint.component(name='plone.constructor')
class Constructor(ConditionalBlueprint):
    def __iter__(self):
        type_key = defaultMatcher(self.options, 'type-key',
                                  self.name, 'type', ('portal_type', 'Type'))
        path_key = defaultMatcher(self.options, 'path-key',
                                  self.name, 'path')
        required = bool(self.options.get('required', 0))
        empty = bool(self.options.get('empty', 1))

        for item in self.previous:
            if self.condition(item):
                constructInstance(item, type_key, path_key, required, empty)
            yield item
