# -*- coding: utf-8 -*-
from Acquisition import aq_base
from plone import api
from plone.api.exc import InvalidParameterError
from transmogrifier.blueprints import ConditionalBlueprint
from venusianconfiguration import configure


@configure.transmogrifier.blueprint.component(name='plone.placeful_workflow.get')  # noqa
class GetPlacefulWorkflow(ConditionalBlueprint):
    def __iter__(self):
        try:
            tool = api.portal.get_tool('portal_placeful_workflow')
        except InvalidParameterError:
            tool = None
        for item in self.previous:
            if tool and self.condition(item):
                obj = item['_object']
                config = tool.getWorkflowPolicyConfig(obj)
                if config is not None and (config.getPolicyInId() or
                                           config.getPolicyBelowId()):
                    item['_workflow_policy_in'] = config.getPolicyInId()
                    item['_workflow_policy_below'] = config.getPolicyBelowId()
            yield item


# noinspection PyProtectedMember
def updateRoleMappings(container):
    wftool = api.portal.get_tool('portal_workflow')
    wfs = {}
    for id_ in wftool.objectIds():
        wf = wftool.getWorkflowById(id_)
        if hasattr(aq_base(wf), 'updateRoleMappingsFor'):
            wfs[id_] = wf
    count = wftool._recursiveUpdateRoleMappings(aq_base(container), wfs)
    return count


@configure.transmogrifier.blueprint.component(name='plone.placeful_workflow.set')  # noqa
class SetPlacefulWorkflow(ConditionalBlueprint):
    def __iter__(self):
        key = '_workflow_policy_in'
        try:
            tool = api.portal.get_tool('portal_placeful_workflow')
        except InvalidParameterError:
            tool = None

        for item in self.previous:
            if tool and self.condition(item) and key in item:
                obj = api.content.get(path=item['_path'])

                # Init placeful workflow policy config when required
                if tool.getWorkflowPolicyConfig(obj) is None:
                    local_tool = obj.manage_addProduct['CMFPlacefulWorkflow']
                    local_tool.manage_addWorkflowPolicyConfig()

                # Set the policy
                config = tool.getWorkflowPolicyConfig(obj)
                config.setPolicyIn(item.get('_workflow_policy_in', ''))
                config.setPolicyBelow(item.get('_workflow_policy_below', ''))

                # Update security
                updateRoleMappings(obj)
            yield item
