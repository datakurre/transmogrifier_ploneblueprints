import posixpath
import Acquisition

from plone import api
from venusianconfiguration import configure
from transmogrifier.blueprints import ConditionalBlueprint
from transmogrifier.utils import defaultMatcher
from transmogrifier_ploneblueprints.utils import traverse


# from collective/transmogrifier/sections/constructor.py
# by rpatterson, regebro, mjpieters, optilude, csenger

import logging
logger = logging.getLogger('transmogrifier')


def constructInstance(item, type_key_matcher, path_key_matcher, required):
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

    path = path.encode('ASCII')
    container, id_ = posixpath.split(path.strip('/'))
    
    if not id_: # site root should exist
        return

    context = traverse(portal, container, None)
    if context is None:
        error = 'Container %s does not exist for item %s' % (
            container, path)
        if required:
            raise KeyError(error)
        logger.warn(error)
        return

    # noinspection PyUnresolvedReferences
    if getattr(Acquisition.aq_base(context), id_, None) is not None:  # exists
        return
    
    # noinspection PyProtectedMember
    obj = fti._constructInstance(context, id_)

    # For CMF <= 2.1 (aka Plone 3)
    if hasattr(fti, '_finishConstruction'):
        # noinspection PyProtectedMember
        obj = fti._finishConstruction(obj)

    if obj.getId() != id_:
        item[path_key] = posixpath.join(container, obj.getId())



@configure.transmogrifier.blueprint.component(name='plone.constructor')
class Constructor(ConditionalBlueprint):
    def __iter__(self):
        type_key = defaultMatcher(self.options, 'type-key',
                                  self.name, 'type', ('portal_type', 'Type'))
        path_key = defaultMatcher(self.options, 'path-key',
                                  self.name, 'path')
        required = bool(self.options.get('required'))

        for item in self.previous:
            if self.condition(item):
                constructInstance(item, type_key, path_key, required)
            yield item
