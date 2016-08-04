# -*- coding: utf-8 -*-
from plone import api
from Products.CMFCore.utils import getToolByName
from transmogrifier.blueprints import ConditionalBlueprint
from transmogrifier_ploneblueprints.utils import traverse
from venusianconfiguration import configure


@configure.transmogrifier.blueprint.component(
    name='plone.workflow_history.set')
class SetWorkflow(ConditionalBlueprint):
    def __iter__(self):
        portal = api.portal.get()
        wftool = getToolByName(portal, 'portal_workflow')
        for item in self.previous:
            if self.condition(item):
                ob = traverse(portal, item['_path'])
                ob.workflow_history = item['_workflow_history'] or {}
#               if 'simple_publication_workflow' in ob.workflow_history:
#                   ob.workflow_history['plone_workflow'] = \
#                       ob.workflow_history['simple_publication_workflow']
                for wf in wftool.getWorkflowsFor(ob):
                    wf.updateRoleMappingsFor(ob)
            yield item
