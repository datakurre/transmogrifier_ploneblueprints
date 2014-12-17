from venusianconfiguration import configure
import posixpath

from transmogrifier.blueprints import ConditionalBlueprint
from transmogrifier.utils import defaultMatcher
from transmogrifier_ploneblueprints.utils import traverse

from Acquisition import aq_base
from Products.CMFCore.utils import getToolByName

# collective/transmogrifier/sections/constructor.py
# by rpatterson, regebro, mjpieters, optilude, csenger

import logging
logger = logging.getLogger('transmogrifier')


@configure.transmogrifier.blueprint.component(name='plone.constructor')
class Constructor(ConditionalBlueprint):
    def _handle(self, item, ttool, typekeyMatcher, pathkeyMatcher, required):
        keys = item.keys()
        typekey = typekeyMatcher(*keys)[0]
        pathkey = pathkeyMatcher(*keys)[0]

        if not (typekey and pathkey):             # not enough info
            return

        type_, path = item[typekey], item[pathkey]

        fti = ttool.getTypeInfo(type_)
        if fti is None:                           # not an existing type
            return

        path = path.encode('ASCII')
        container, id = posixpath.split(path.strip('/'))
        context = traverse(self.transmogrifier.context, container, None)
        if context is None:
            error = 'Container %s does not exist for item %s' % (
                container, path)
            if required:
                raise KeyError(error)
            logger.warn(error)
            return

        if getattr(aq_base(context), id, None) is not None: # item exists
            return

        obj = fti._constructInstance(context, id)

        # For CMF <= 2.1 (aka Plone 3)
        if hasattr(fti, '_finishConstruction'):
            obj = fti._finishConstruction(obj)

        if obj.getId() != id:
            item[pathkey] = posixpath.join(container, obj.getId())

    def __iter__(self):
        ttool = getToolByName(self.transmogrifier.context, 'portal_types')
        typekeyMatcher = defaultMatcher(
            self.options, 'type-key', self.name, 'type', ('portal_type', 'Type'))
        pathkeyMatcher = defaultMatcher(
            self.options, 'path-key', self.name, 'path')
        required = bool(self.options.get('required'))

        for item in self.previous:
            if self.condition(item):
                self._handle(item, ttool, typekeyMatcher, pathkeyMatcher, required)
            yield item
