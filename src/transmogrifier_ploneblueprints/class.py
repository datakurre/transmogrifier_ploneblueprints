import importlib
from io import BytesIO
from pprint import pprint
from Products.CMFCore.utils import getToolByName
from plone.dexterity.interfaces import IDexterityFTI
from venusianconfiguration import configure
from transmogrifier.blueprints import ConditionalBlueprint

import logging

logger = logging.getLogger('transmogrifier')


@configure.transmogrifier.blueprint.component(name='plone.change_class')
class ChangeClassSection(ConditionalBlueprint):

    def _change_class(self, ob, item):
        get_type = getattr(ob, 'getPortalTypeName', lambda x: '')
        if get_type() not in self.options.get('types', []):
            return
        portal_types = getToolByName(self.transmogrifier.context,
                                     'portal_types')
        fti = portal_types.get(item['_type'])
        is_dexterity = IDexterityFTI.providedBy(fti)
        # TODO: Not implemented yet
        if is_dexterity:
            cls = None
        else:
            cls = None

        if cls:
            module_name, class_name = cls.rsplit('.', 1)
            module = importlib.import_module(module_name)
            ob.__class__ = getattr(module, class_name)
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
