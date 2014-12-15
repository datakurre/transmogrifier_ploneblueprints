import importlib
from Products.Archetypes.ArchetypeTool import _types
from Products.CMFCore.utils import getToolByName
from plone.dexterity.interfaces import IDexterityFTI
from venusianconfiguration import configure
from transmogrifier.blueprints import ConditionalBlueprint

import logging

logger = logging.getLogger('transmogrifier')


@configure.transmogrifier.blueprint.component(name='plone.change_class')
class ChangeClassSection(ConditionalBlueprint):

    def _change_class(self, ob, item):
        get_type = getattr(ob, 'getPortalTypeName', lambda x: None)
        if get_type() not in self.options.get('types', []):
            return
        portal_types = getToolByName(self.transmogrifier.context,
                                     'portal_types')
        fti = portal_types.get(item['_type'])
        is_dexterity = IDexterityFTI.providedBy(fti)

        if is_dexterity:
            module_name, class_name = fti.klass.rsplit('.', 1)
            module = importlib.import_module(module_name)
            class_ = getattr(module, class_name)
        else:
            key = ".".join([fti.product, fti.id])
            class_ = _types[key].klass

        ob.__class__ = class_
        ob._p_changed = True

    def __iter__(self):
        for item in self.previous:
            if self.condition(item):
                try:
                    context = self.transmogrifier.context
                    path = "".join(context.getPhysicalPath()) + item['_path']
                    ob = context.unrestrictedTraverse(path)
                except KeyError:
                    pass
                else:
                    self._change_class(ob, item)
            yield item
