# -*- coding: utf-8 -*-
from Products.CMFCore.utils import getToolByName
from transmogrifier.blueprints import ConditionalBlueprint
from transmogrifier_ploneblueprints.utils import traverse
from venusianconfiguration import configure
from plone import api
from Acquisition import aq_base

@configure.transmogrifier.blueprint.component(name='plone.placeful_workflow.get')  # noqa
class GetPlacefulWorkflow(ConditionalBlueprint):
    def __iter__(self):
        portal = api.portal.get()
        pwtool = getToolByName(portal, "portal_placeful_workflow")
        for item in self.previous:
            if self.condition(item):
                ob = item['_object']
                config = pwtool.getWorkflowPolicyConfig(ob)
                if config is not None and (config.getPolicyInId()
                                           or config.getPolicyBelowId()):
                    item['_workflow_policy_in'] = config.getPolicyInId()
                    item['_workflow_policy_below'] = config.getPolicyBelowId()
            yield item


def updateRoleMappings(container):
    wftool = getToolByName(container, "portal_workflow")
    wfs = {}
    for id_ in wftool.objectIds():
        wf = wftool.getWorkflowById(id_)
        if hasattr(aq_base(wf), "updateRoleMappingsFor"):
            wfs[id_] = wf
    count = wftool._recursiveUpdateRoleMappings(aq_base(container), wfs)
    return count 


@configure.transmogrifier.blueprint.component(name='plone.placeful_workflow.set')  # noqa
class SetPlacefulWorkflow(ConditionalBlueprint):
    def __iter__(self):
        portal = api.portal.get()
        pwtool = getToolByName(portal, "portal_placeful_workflow")
        for item in self.previous:
            if self.condition(item) and '_workflow_policy_in' in item:
                ob = traverse(portal, item['_path'])

                # Init placeful workflow policy config when required
                if pwtool.getWorkflowPolicyConfig(ob) is None:
                    local_tool = ob.manage_addProduct["CMFPlacefulWorkflow"]
                    local_tool.manage_addWorkflowPolicyConfig() 
                
                # Set the policy
                config = pwtool.getWorkflowPolicyConfig(ob)
                config.setPolicyIn(item.get('_workflow_policy_in', ''))
                config.setPolicyBelow(item.get('_workflow_policy_below', ''))

                # Update security
                updateRoleMappings(ob) 
            yield item

